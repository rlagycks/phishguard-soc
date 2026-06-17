"""Admin endpoints for Gmail watch management and OAuth flow."""

import logging

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import orm
from app.services import gmail_client
from app.services.auth import create_access_token, create_refresh_token, decode_token

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter(tags=["admin"])


# ── OAuth flow ────────────────────────────────────────────────────────────────

@router.get("/auth/login")
def auth_login():
    """Redirect to Google consent screen."""
    return RedirectResponse(url=gmail_client.get_auth_url())


@router.get("/auth/callback")
def auth_callback(code: str, state: str = "", db: Session = Depends(get_db)):
    """Exchange auth code for tokens, set up Gmail watch, issue JWT, redirect to the dashboard."""
    try:
        email = gmail_client.exchange_code(code, state)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"OAuth exchange failed: {e}")

    if not email:
        try:
            email = gmail_client.get_authenticated_email()
        except Exception as e:
            logger.warning("Failed to get authenticated email: %s", e)
            email = settings.GMAIL_ACCOUNT or "unknown@gmail.com"

    watch_param = "active"
    try:
        watch_resp = gmail_client.setup_watch(email=email)
        _persist_watch(watch_resp, db, email=email)
    except Exception as e:
        logger.warning("Watch setup failed after OAuth: %s", e)
        watch_param = "failed"

    access_token = create_access_token(email)
    refresh_token = create_refresh_token(email)

    redirect_url = (
        f"{settings.FRONTEND_URL or settings.STREAMLIT_URL}"
        f"?access_token={access_token}"
        f"&refresh_token={refresh_token}"
        f"&watch={watch_param}"
    )
    return RedirectResponse(url=redirect_url, status_code=303)


class RefreshRequest(BaseModel):
    refresh_token: str


@router.post("/auth/refresh")
def refresh_access_token(body: RefreshRequest):
    """Issue a new access token using a valid refresh token."""
    payload = decode_token(body.refresh_token)
    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
    email = payload.get("email", payload.get("sub", ""))
    return {"access_token": create_access_token(email)}


@router.get("/auth/verify")
def verify_token(authorization: str = Header(default="")):
    """Verify an access token. Used by Streamlit dashboard to check auth state."""
    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(status_code=401, detail="Missing token")
    payload = decode_token(token)
    if payload is None or payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid or expired access token")
    return {"valid": True, "email": payload.get("email", ""), "exp": payload.get("exp")}


# ── Watch management ──────────────────────────────────────────────────────────

@router.post("/api/admin/watch/setup")
def setup_watch(db: Session = Depends(get_db)):
    try:
        email = gmail_client.get_authenticated_email()
        resp = gmail_client.setup_watch(email=email)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    _persist_watch(resp, db, email=email)
    return resp


@router.post("/api/admin/watch/renew")
def renew_watch(db: Session = Depends(get_db)):
    """Renew Gmail watch (must be called before 7-day expiry)."""
    try:
        email = gmail_client.get_authenticated_email()
    except Exception:
        email = ""
    try:
        gmail_client.stop_watch(email=email)
    except Exception:
        pass
    try:
        resp = gmail_client.setup_watch(email=email)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    _persist_watch(resp, db, email=email)
    return {"status": "renewed", **resp}


@router.get("/api/admin/watch/status")
def watch_status(db: Session = Depends(get_db)):
    watch = db.query(orm.WatchStatus).first()
    if not watch:
        return {"status": "not_configured"}
    return {
        "email_address": watch.email_address,
        "history_id": watch.history_id,
        "expiration_ms": watch.expiration_ms,
        "updated_at": watch.updated_at,
    }


# ── Helpers ───────────────────────────────────────────────────────────────────

def _persist_watch(resp: dict, db: Session, email: str = "") -> None:
    if email:
        watch = db.query(orm.WatchStatus).filter_by(email_address=email).first()
    else:
        watch = db.query(orm.WatchStatus).first()
    if watch:
        watch.expiration_ms = int(resp.get("expiration", 0))
        watch.history_id = str(resp.get("historyId", watch.history_id or ""))
    else:
        db.add(orm.WatchStatus(
            email_address=email or settings.GMAIL_ACCOUNT,
            history_id=str(resp.get("historyId", "")),
            expiration_ms=int(resp.get("expiration", 0)),
        ))
    db.commit()
