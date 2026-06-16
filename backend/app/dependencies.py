"""Shared FastAPI dependencies."""
from __future__ import annotations

from fastapi import Header, HTTPException
from app.services.auth import decode_token


def get_current_user(authorization: str = Header(default="")) -> str:
    """Extract and validate the Bearer JWT. Returns the authenticated email."""
    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    payload = decode_token(token)
    if payload is None or payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid or expired access token")
    email = payload.get("email") or payload.get("sub", "")
    if not email:
        raise HTTPException(status_code=401, detail="Token missing email claim")
    return email
