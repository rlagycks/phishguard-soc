"""Streamlit authentication guard — cookie-based JWT session management.

Token strategy:
  - Access token  (15 min) : stored in session_state + browser cookie
  - Refresh token (7 days) : stored in session_state + browser cookie
  - Cookies are non-HttpOnly (Streamlit component limitation without nginx)
  - On expired access token: auto-refresh via POST /auth/refresh
  - On expired refresh token: redirect to login

Note: CookieController renders a hidden iframe component. On the very first
page load the component may not have values yet (double-render problem).
This causes a brief login flash before the dashboard appears — acceptable
for a demo environment.
"""

from __future__ import annotations

import requests
import streamlit as st

_COOKIE_ACCESS = "soc_access"
_COOKIE_REFRESH = "soc_refresh"
_ACCESS_MAX_AGE = 900       # 15 min (seconds)
_REFRESH_MAX_AGE = 604800   # 7 days (seconds)


def _ctrl():
    """Return a CookieController instance, or None if package unavailable."""
    try:
        from streamlit_cookies_controller import CookieController
        return CookieController(key="soc_auth")
    except Exception:
        return None


# ── Token capture ─────────────────────────────────────────────────────────────

def capture_tokens() -> None:
    """Read access/refresh tokens from URL query params (post-OAuth redirect)."""
    access = st.query_params.get("access_token")
    if not access:
        return
    refresh = st.query_params.get("refresh_token", "")
    st.session_state["access_token"] = access
    if refresh:
        st.session_state["refresh_token"] = refresh
    ctrl = _ctrl()
    if ctrl is not None:
        ctrl.set(_COOKIE_ACCESS, access, max_age=_ACCESS_MAX_AGE)
        if refresh:
            ctrl.set(_COOKIE_REFRESH, refresh, max_age=_REFRESH_MAX_AGE)
    st.query_params.clear()


# ── Cookie fallback ────────────────────────────────────────────────────────────

def _load_from_cookies() -> bool:
    """Try to populate session_state from browser cookies."""
    ctrl = _ctrl()
    if ctrl is None:
        return False
    access = ctrl.get(_COOKIE_ACCESS)
    if not access:
        return False
    st.session_state["access_token"] = access
    refresh = ctrl.get(_COOKIE_REFRESH)
    if refresh:
        st.session_state["refresh_token"] = refresh
    return True


# ── Token refresh ──────────────────────────────────────────────────────────────

def _try_refresh(api_base: str) -> bool:
    """Attempt to get a new access token using the stored refresh token."""
    refresh = st.session_state.get("refresh_token")
    if not refresh:
        ctrl = _ctrl()
        if ctrl is not None:
            refresh = ctrl.get(_COOKIE_REFRESH)
    if not refresh:
        return False
    try:
        r = requests.post(
            f"{api_base}/auth/refresh",
            json={"refresh_token": refresh},
            timeout=5,
        )
        if r.status_code == 200:
            new_access = r.json()["access_token"]
            st.session_state["access_token"] = new_access
            ctrl = _ctrl()
            if ctrl is not None:
                ctrl.set(_COOKIE_ACCESS, new_access, max_age=_ACCESS_MAX_AGE)
            return True
    except Exception:
        pass
    return False


# ── Auth check ─────────────────────────────────────────────────────────────────

def is_authenticated(api_base: str) -> bool:
    """Return True if the current session has a valid (or refreshable) access token."""
    if "access_token" not in st.session_state:
        _load_from_cookies()

    access = st.session_state.get("access_token")
    if not access:
        return False

    try:
        r = requests.get(
            f"{api_base}/auth/verify",
            headers={"Authorization": f"Bearer {access}"},
            timeout=5,
        )
        if r.status_code == 200:
            st.session_state["user_email"] = r.json().get("email", "")
            return True
        if r.status_code == 401:
            return _try_refresh(api_base)
    except Exception:
        pass

    _clear_auth()
    return False


# ── Login page ─────────────────────────────────────────────────────────────────

def render_login(api_base: str) -> None:
    """Render a centered login page with Google OAuth button."""
    st.title("🛡️ Phishing SOC Dashboard")
    st.divider()
    _, col, _ = st.columns([1, 2, 1])
    with col:
        st.markdown("### 로그인이 필요합니다")
        st.info(
            "Google 계정으로 로그인하면 Gmail이 자동으로 연결되고\n"
            "피싱 메일 실시간 모니터링이 시작됩니다."
        )
        st.link_button(
            "🔐   Google로 로그인",
            f"{api_base}/auth/login",
            use_container_width=True,
        )


# ── Logout / helpers ───────────────────────────────────────────────────────────

def logout() -> None:
    _clear_auth()


def auth_header() -> dict[str, str]:
    """Return an Authorization header dict for API calls."""
    token = st.session_state.get("access_token", "")
    return {"Authorization": f"Bearer {token}"} if token else {}


def _clear_auth() -> None:
    for key in ("access_token", "refresh_token", "user_email"):
        st.session_state.pop(key, None)
    ctrl = _ctrl()
    if ctrl is not None:
        try:
            ctrl.remove(_COOKIE_ACCESS)
            ctrl.remove(_COOKIE_REFRESH)
        except Exception:
            pass
