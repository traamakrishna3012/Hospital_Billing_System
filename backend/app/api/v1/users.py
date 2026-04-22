"""
User/Staff management routes — admin only.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func

from app.core.deps import CurrentUser, DBSession, TenantID, require_role
from app.core.security import hash_password
from app.models.user import User
from app.schemas.schemas import (
    PaginatedResponse,
    UserCreateRequest,
    UserResponse,
    UserUpdateRequest,
)

router = APIRouter(prefix="/users", tags=["Staff Management"])


@router.get("", response_model=PaginatedResponse, summary="List staff users")
async def list_users(
    db: DBSession,
    tenant_id: TenantID,
    current_user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """List all staff users for the clinic. Admin only."""
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    count_query = select(func.count(User.id)).where(User.tenant_id == tenant_id)
    total = (await db.execute(count_query)).scalar() or 0
    total_pages = max(1, (total + page_size - 1) // page_size)

    offset = (page - 1) * page_size
    result = await db.execute(
        select(User)
        .where(User.tenant_id == tenant_id)
        .order_by(User.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    users = result.scalars().all()

    return PaginatedResponse(
        items=[UserResponse.model_validate(u) for u in users],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED, summary="Create staff user")
async def create_user(
    data: UserCreateRequest,
    db: DBSession,
    tenant_id: TenantID,
    current_user: CurrentUser,
):
    """Create a new staff user. Admin only."""
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    # Check if email already exists for this tenant
    existing = await db.execute(
        select(User).where(User.tenant_id == tenant_id, User.email == data.email)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists in your clinic",
        )

    if data.role == "superadmin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot assign superadmin role to clinic staff",
        )

    user = User(
        tenant_id=tenant_id,
        email=data.email,
        password_hash=hash_password(data.password),
        full_name=data.full_name,
        phone=data.phone,
        role=data.role,
        is_approved=True,  # Staff created by an admin are auto-approved
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return UserResponse.model_validate(user)


@router.put("/{user_id}", response_model=UserResponse, summary="Update staff user")
async def update_user(
    user_id: UUID,
    data: UserUpdateRequest,
    db: DBSession,
    tenant_id: TenantID,
    current_user: CurrentUser,
):
    """Update a staff user. Admin only."""
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    result = await db.execute(
        select(User).where(User.id == user_id, User.tenant_id == tenant_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if getattr(data, "role", None) == "superadmin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot assign superadmin role to clinic staff",
        )

    # Prevent deactivating the last admin
    if data.is_active is False and user.role == "admin":
        admin_count = (await db.execute(
            select(func.count(User.id)).where(
                User.tenant_id == tenant_id,
                User.role == "admin",
                User.is_active == True,  # noqa: E712
            )
        )).scalar()
        if admin_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot deactivate the last admin user",
            )

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(user, key, value)

    await db.commit()
    await db.refresh(user)
    return UserResponse.model_validate(user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete staff user")
async def delete_user(
    user_id: UUID,
    db: DBSession,
    tenant_id: TenantID,
    current_user: CurrentUser,
):
    """Remove a staff user. Admin only. Cannot delete yourself."""
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot delete your own account",
        )

    result = await db.execute(
        select(User).where(User.id == user_id, User.tenant_id == tenant_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    await db.delete(user)
    await db.commit()
