"""Authentication helpers for securing helper API access."""

from __future__ import annotations

from fastapi import Depends, Header, HTTPException, status

from helper_app.config import ensure_token

TOKEN = ensure_token()


def verify_token(x_zenith_token: str = Header(...)) -> None:
    if x_zenith_token != TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
        )


def token_dependency(token: str = Depends(verify_token)) -> None:  # pragma: no cover - FastAPI wiring
    return token

