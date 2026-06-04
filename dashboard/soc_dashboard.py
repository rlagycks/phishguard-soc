"""SOC Dashboard — Streamlit UI.

Run with:
  cd dashboard
  streamlit run soc_dashboard.py

Or from project root:
  streamlit run dashboard/soc_dashboard.py
"""

import os
import sys
import time
from datetime import datetime

import plotly.express as px
import requests
import streamlit as st

# Ensure auth_guard is importable regardless of working directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from auth_guard import capture_tokens, is_authenticated, render_login, logout, auth_header

# ── Page config (must be first Streamlit command) ─────────────────────────────

st.set_page_config(
    page_title="Phishing SOC Dashboard",
    page_icon="🛡️",
    layout="wide",
)

# ── Auth guard ─────────────────────────────────────────────────────────────────

_API_DEFAULT = os.getenv("API_BASE_URL", "http://localhost:8000")

capture_tokens()

if not is_authenticated(_API_DEFAULT):
    render_login(_API_DEFAULT)
    st.stop()

# ── Sidebar ───────────────────────────────────────────────────────────────────

API_BASE = st.sidebar.text_input("API Base URL", value=_API_DEFAULT)
AUTO_REFRESH = st.sidebar.checkbox("Auto-refresh (10s)", value=True)

user_email = st.session_state.get("user_email", "")
if user_email:
    st.sidebar.caption(f"👤 {user_email}")
st.sidebar.divider()
if st.sidebar.button("🚪 로그아웃"):
    logout()
    st.rerun()

REFRESH_INTERVAL = 10


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get(path: str) -> dict | list | None:
    try:
        r = requests.get(f"{API_BASE}{path}", headers=auth_header(), timeout=5)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"API error ({path}): {e}")
        return None


def _patch(path: str, payload: dict) -> dict | None:
    try:
        r = requests.patch(f"{API_BASE}{path}", json=payload, headers=auth_header(), timeout=5)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"API error: {e}")
        return None


def _risk_color(level: str) -> str:
    return {"dangerous": "🔴", "suspicious": "🟡", "normal": "🟢"}.get(level, "⚪")


# ── Header ────────────────────────────────────────────────────────────────────

st.title("🛡️ Phishing SOC Dashboard")
st.caption(f"마지막 로드: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# ── Stats row ─────────────────────────────────────────────────────────────────

stats = _get("/api/dashboard/stats")
if stats:
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("총 분석", stats["total"])
    c2.metric("정상", stats["normal"])
    c3.metric("의심", stats["suspicious"])
    c4.metric("위험 🔴", stats["dangerous"])
    c5.metric("격리", stats["quarantined"])
    avg = stats.get("avg_analysis_ms")
    c6.metric("평균 분석 시간", f"{avg:.0f} ms" if avg else "—")

st.divider()

# ── Two-column layout ─────────────────────────────────────────────────────────

left, right = st.columns([3, 2])

with left:
    st.subheader("📋 최근 탐지 목록")

    risk_filter = st.selectbox(
        "위험도 필터",
        options=["전체", "dangerous", "suspicious", "normal"],
        index=0,
    )
    param = "" if risk_filter == "전체" else f"?risk_level={risk_filter}"
    emails = _get(f"/api/dashboard/emails{param}") or []

    if not emails:
        st.info("탐지된 이메일이 없습니다.")
    else:
        for email in emails:
            level = email.get("risk_level", "unknown")
            score = email.get("final_score", 0) or 0
            icon = _risk_color(level)
            with st.expander(
                f"{icon} [{level.upper()}] {email.get('subject', '(제목 없음)')} | 점수: {score:.2f}",
                expanded=False,
            ):
                st.write(f"**발신자:** {email.get('sender', '—')}")
                st.write(f"**수신 시각:** {email.get('received_at', '—')}")
                st.write(f"**상태:** {email.get('status', '—')}")

                email_id = email["id"]
                col_a, col_b, col_c = st.columns(3)
                if col_a.button("상세 보기", key=f"detail_{email_id}"):
                    st.session_state["selected_email_id"] = email_id
                if col_b.button("정상 처리", key=f"normal_{email_id}"):
                    _patch(f"/api/dashboard/emails/{email_id}/status", {"status": "normal"})
                    st.rerun()
                if col_c.button("격리", key=f"quarantine_{email_id}"):
                    _patch(f"/api/dashboard/emails/{email_id}/status", {"status": "quarantined"})
                    st.rerun()

with right:
    st.subheader("📊 위험도 분포")

    if stats and stats["total"] > 0:
        fig_pie = px.pie(
            names=["정상", "의심", "위험"],
            values=[stats["normal"], stats["suspicious"], stats["dangerous"]],
            color_discrete_sequence=["#2ecc71", "#f39c12", "#e74c3c"],
            hole=0.4,
        )
        fig_pie.update_layout(showlegend=True, margin=dict(t=0, b=0, l=0, r=0))
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("데이터 없음")

    st.subheader("📈 일별 탐지 추이")
    daily = _get("/api/dashboard/daily") or []
    if daily:
        fig_bar = px.bar(
            daily,
            x="day",
            y=["total", "dangerous"],
            barmode="group",
            color_discrete_map={"total": "#3498db", "dangerous": "#e74c3c"},
            labels={"day": "날짜", "value": "건수"},
        )
        fig_bar.update_layout(margin=dict(t=0, b=0, l=0, r=0))
        st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.info("일별 데이터 없음")

# ── Email detail panel ────────────────────────────────────────────────────────

selected_id = st.session_state.get("selected_email_id")
if selected_id:
    st.divider()
    st.subheader("🔍 이메일 상세 분석")
    detail = _get(f"/api/dashboard/emails/{selected_id}")
    if detail:
        dc1, dc2, dc3, dc4 = st.columns(4)
        dc1.metric("NLP 점수", f"{detail.get('nlp_score', 0):.3f}")
        dc2.metric("URL 점수", f"{detail.get('url_score', 0):.3f}")
        dc3.metric("Rule 점수", f"{detail.get('rule_score', 0):.3f}")
        dc4.metric("최종 점수", f"{detail.get('final_score', 0):.3f}")

        st.write(f"**발신자:** {detail.get('sender', '—')}")
        st.write(f"**제목:** {detail.get('subject', '—')}")
        st.write(f"**위험도:** {detail.get('risk_level', '—').upper()}")
        st.write(f"**상태:** {detail.get('status', '—')}")

        if detail.get("body_preview"):
            st.text_area("본문 미리보기", detail["body_preview"], height=100, disabled=True)

        urls = detail.get("urls_found") or []
        if urls:
            st.write("**추출된 URL:**")
            for url in urls[:10]:
                st.code(url)

        model_details = detail.get("model_details") or {}
        features = model_details.get("nlp_top_features") or []
        if features:
            st.write("**NLP 탐지 근거 (상위 키워드):**")
            st.write(", ".join(features))

        url_details = model_details.get("url_details") or []
        if url_details:
            st.write("**URL 분석 결과:**")
            for u in url_details[:5]:
                st.write(
                    f"- `{u.get('url', '')[:60]}` → 점수: {u.get('score', 0):.3f}"
                    f" | HTTPS: {u.get('is_https')} | IP: {u.get('is_ip')}"
                )

# ── Auto-refresh ──────────────────────────────────────────────────────────────

if AUTO_REFRESH:
    time.sleep(REFRESH_INTERVAL)
    st.rerun()
