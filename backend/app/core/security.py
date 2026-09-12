"""Minimal auth/session handling for a single-user app.

Not internet-facing multi-tenant auth — just enough to keep the API from
being wide open if it's ever exposed beyond localhost. Swap for real auth
(OAuth, etc.) before deploying anywhere multi-user.
"""
from __future__ import annotations

import hmac

from fastapi import Header, HTTPException, status

from app.config import get_settings

settings = get_settings()


def verify_session_token(x_session_token: str | None = Header(default=None)) -> None:
    """FastAPI dependency: require a shared-secret header to match SESSION_SECRET.

    Skipped entirely (no-op) when SESSION_SECRET is left at its insecure
    default, so local dev works without extra setup — but that means this
    must never be the config used in a real deployment.
    """
    if settings.session_secret == "dev-secret-change-me":
        return

    if x_session_token is None or not hmac.compare_digest(x_session_token, settings.session_secret):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing session token")
