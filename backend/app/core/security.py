"""
Security utilities: JWT token management and password hashing.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID
import uuid

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings

settings = get_settings()

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ── Password Utilities ───────────────────────────────────────

def hash_password(password: str) -> str:
    """Hash a plaintext password."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


# ── JWT Token Utilities ──────────────────────────────────────

def create_access_token(
    user_id: UUID,
    tenant_id: UUID | None,
    role: str,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """Create a JWT access token."""
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    payload = {
        "jti": str(uuid.uuid4()),
        "sub": str(user_id),
        "role": role,
        "type": "access",
        "iat": now,
        "exp": expire,
    }
    if tenant_id is not None:
        payload["tenant_id"] = str(tenant_id)
    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(user_id: UUID, tenant_id: UUID | None) -> str:
    """Create a JWT refresh token with extended expiry."""
    now = datetime.now(timezone.utc)
    expire = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    payload = {
        "jti": str(uuid.uuid4()),
        "sub": str(user_id),
        "type": "refresh",
        "iat": now,
        "exp": expire,
    }
    if tenant_id is not None:
        payload["tenant_id"] = str(tenant_id)

    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict[str, Any] | None:
    """
    Decode and validate a JWT token.
    Returns the payload dict or None if invalid/expired.
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return payload
    except JWTError:
        return None
