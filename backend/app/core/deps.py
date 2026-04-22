"""
FastAPI dependencies for authentication, authorization, and database access.
Enforces tenant isolation at the dependency level.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.security import decode_token
from app.models.user import User
from app.models.tenant import Tenant
from app.models.token_blocklist import TokenBlocklist

# Bearer token scheme
bearer_scheme = HTTPBearer(auto_error=True)

# Type alias for database session dependency
DBSession = Annotated[AsyncSession, Depends(get_async_session)]


async def get_current_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(HTTPBearer(auto_error=False))],
    db: DBSession,
) -> User:
    """
    Validate the JWT token and return the authenticated user with approval status.
    Checks HttpOnly cookie first, then falls back to Authorization Bearer header.
    Raises 401 if token is invalid or user not found.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Try HttpOnly cookie first, then Bearer header
    token = request.cookies.get("access_token")
    if not token and credentials:
        token = credentials.credentials
    if not token:
        raise credentials_exception

    payload = decode_token(token)
    if payload is None or payload.get("type") != "access":
        raise credentials_exception

    user_id_str = payload.get("sub")
    jti = payload.get("jti")
    if user_id_str is None or jti is None:
        raise credentials_exception

    # Check if token is blocklisted
    is_blocklisted = await db.execute(select(TokenBlocklist).where(TokenBlocklist.jti == jti))
    if is_blocklisted.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked/logged out",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = UUID(user_id_str)
    except ValueError:
        raise credentials_exception

    result = await db.execute(
        select(User).where(User.id == user_id, User.is_active == True)  # noqa: E712
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception

    return user


# Type alias for current user dependency
CurrentUser = Annotated[User, Depends(get_current_user)]


def require_role(*roles: str):
    """
    Dependency factory: restrict access to users with specific roles.

    Usage:
        @router.get("/admin-only", dependencies=[Depends(require_role("admin"))])
    """
    async def _check_role(current_user: CurrentUser) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role: {', '.join(roles)}",
            )
        return current_user

    return _check_role


def require_superadmin():
    """Dependency: restrict access to superadmin users only."""
    return require_role("superadmin")


async def get_tenant_id(current_user: CurrentUser, db: DBSession) -> UUID:
    """
    Extract tenant_id from the current user and verify clinic approval.
    Raises 403 if the clinic is pending approval.
    """
    if current_user.tenant_id is None:
        # Superadmins don't have a tenant_id but might use these endpoints if they act as a tenant
        if current_user.role == "superadmin":
            return None 
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not scoped to a clinic.",
        )
    
    # Enforce clinic approval
    if not current_user.is_approved:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your clinic account is pending approval by the Super Admin. Please contact support."
        )

    return current_user.tenant_id


# Type alias for tenant ID dependency
TenantID = Annotated[UUID, Depends(get_tenant_id)]
