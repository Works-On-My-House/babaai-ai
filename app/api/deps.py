from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

import httpx
from fastapi import Header, HTTPException, status
from jose import jwt
from jose.exceptions import JWTError

from app.core.config import get_settings

logger = logging.getLogger(__name__)
_jwks_cache: dict[str, Any] | None = None


def require_service_token(
    x_service_token: str | None = Header(default=None, alias="X-Service-Token"),
) -> None:
    settings = get_settings()
    if not x_service_token or x_service_token != settings.ai_service_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid service token",
        )


def _load_jwks() -> dict[str, Any]:
    global _jwks_cache
    if _jwks_cache is not None:
        return _jwks_cache
    settings = get_settings()
    response = httpx.get(settings.core_jwks_url, timeout=5.0)
    response.raise_for_status()
    _jwks_cache = response.json()
    return _jwks_cache


def get_current_user_id(authorization: str | None = Header(default=None)) -> UUID:
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    token = authorization.removeprefix("Bearer ").strip()
    try:
        jwks = _load_jwks()
        payload = jwt.decode(token, jwks, algorithms=["RS256"], options={"verify_aud": False})
        subject = payload.get("sub")
        if not subject:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token subject",
            )
        return UUID(str(subject))
    except (JWTError, ValueError) as exc:
        logger.debug("JWT validation failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        ) from exc
