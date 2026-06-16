from __future__ import annotations

import hashlib
import hmac
import logging
from enum import StrEnum
from typing import Any
from uuid import UUID

import httpx
from fastapi import Depends, Header, HTTPException, status
from jose import jwt
from jose.exceptions import JWTError
from pydantic import BaseModel, Field

from app.core import quota
from app.core.config import get_settings

logger = logging.getLogger(__name__)
_jwks_cache: dict[str, Any] | None = None


def require_service_token(
    x_service_token: str | None = Header(default=None, alias="X-Service-Token"),
) -> None:
    """Verify the shared service secret for internal core→ai calls (proposals, reindex).

    Stores only the SHA-256 hash of the secret (never the plaintext) and verifies by hashing the
    incoming header, with a constant-time compare — same idea as a password ``matches()``, but with
    the fast hash the codebase already uses for opaque tokens (refresh tokens). A static secret
    keeps this internal hop free of any JWKS/clock dependency. (Instant token revocation at the
    gateway uses a signed token instead; see ClickUp 869dqmbfp.)
    """
    settings = get_settings()
    if not x_service_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid service token",
        )
    received_hash = hashlib.sha256(x_service_token.encode()).hexdigest()
    if not hmac.compare_digest(received_hash, settings.ai_service_token_hash):
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


def _decode_token(authorization: str | None) -> dict[str, Any]:
    """Statelessly verify a core-issued access token (RS256 signature + expiry via JWKS).

    Returns the decoded claims, or raises 401. No DB or per-request core call — core is
    the authority that bakes entitlement into the token; ai is a stateless enforcer.
    """
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token"
        )
    token = authorization.removeprefix("Bearer ").strip()
    try:
        jwks = _load_jwks()
        return jwt.decode(token, jwks, algorithms=["RS256"], options={"verify_aud": False})
    except (JWTError, ValueError) as exc:
        logger.debug("JWT validation failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        ) from exc


class Principal(BaseModel):
    """Authenticated user resolved from the access-token claims."""

    user_id: UUID
    permissions: frozenset[str] = frozenset()

    def has_permission(self, permission: str) -> bool:
        return permission in self.permissions


def current_principal(authorization: str | None = Header(default=None)) -> Principal:
    """FastAPI dependency: any authenticated user (does NOT 403 free users)."""
    payload = _decode_token(authorization)
    subject = payload.get("sub")
    if not subject:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token subject",
        )
    raw_permissions = payload.get("permissions") or []
    try:
        return Principal(user_id=UUID(str(subject)), permissions=frozenset(raw_permissions))
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token subject",
        ) from exc


def get_current_user_id(principal: Principal = Depends(current_principal)) -> UUID:
    return principal.user_id


class Tier(StrEnum):
    PREMIUM = "premium"
    FREE = "free"


class RoutingDecision(BaseModel):
    """Resolved tier + selected agent for an authenticated request."""

    tier: Tier
    agent_id: str
    # Tokens remaining today for the premium quota; None = no quota enforced (free tier).
    quota_remaining: int | None = Field(default=None)


async def route_request(principal: Principal = Depends(current_principal)) -> RoutingDecision:
    """Tier-routing + quota-check stub.

    ``AI_PRO_SUGGESTIONS`` present → premium (fast) model with a daily token quota (429
    when exceeded). Otherwise → free Ollama tier, no quota. The actual streaming LLM call
    is out of scope for this skeleton (ClickUp 869dqh96c).
    """
    settings = get_settings()
    if not principal.has_permission(settings.ai_pro_permission):
        return RoutingDecision(tier=Tier.FREE, agent_id=settings.default_agent_id)

    limit = settings.premium_daily_token_quota
    if limit <= 0:
        return RoutingDecision(tier=Tier.PREMIUM, agent_id=settings.premium_agent_id)

    used = await quota.get_usage(principal.user_id)
    if used >= limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Daily AI token quota exceeded",
        )
    return RoutingDecision(
        tier=Tier.PREMIUM,
        agent_id=settings.premium_agent_id,
        quota_remaining=max(0, limit - used),
    )
