"""
Clinic settings routes — profile, logo, subscription.

Logo is stored as a base64 data-URL directly in tenant.logo_url.
This avoids ephemeral-filesystem loss on Render / serverless platforms.
"""

from __future__ import annotations

import base64
import io
from uuid import UUID

import magic
from PIL import Image

from fastapi import APIRouter, HTTPException, UploadFile, File, status
from sqlalchemy import select

from app.core.config import get_settings
from app.core.deps import CurrentUser, DBSession, TenantID, require_role
from app.models.tenant import Tenant
from app.schemas.schemas import TenantResponse, TenantUpdateRequest

settings = get_settings()
router = APIRouter(prefix="/clinic", tags=["Clinic Settings"])

ALLOWED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/gif", "image/webp"}


@router.get("", response_model=TenantResponse, summary="Get clinic profile")
async def get_clinic_profile(
    db: DBSession,
    tenant_id: TenantID,
    current_user: CurrentUser,
):
    """Get the current clinic's profile and settings."""
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")
    return TenantResponse.model_validate(tenant)


@router.put("", response_model=TenantResponse, summary="Update clinic profile")
async def update_clinic_profile(
    data: TenantUpdateRequest,
    db: DBSession,
    tenant_id: TenantID,
    current_user: CurrentUser,
):
    """Update clinic profile. Admin only."""
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clinic not found")

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(tenant, key, value)

    await db.commit()
    await db.refresh(tenant)
    return TenantResponse.model_validate(tenant)


@router.post("/logo", response_model=TenantResponse, summary="Upload clinic logo")
async def upload_logo(
    db: DBSession,
    tenant_id: TenantID,
    current_user: CurrentUser,
    file: UploadFile = File(...),
):
    """Upload or replace the clinic logo. Admin only.

    The image is validated via magic bytes, stripped of EXIF metadata,
    converted to a base64 data-URL, and stored directly in the database.
    This means the logo is permanent — no file-system dependency
    that would be wiped on a serverless/Render restart.
    """
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    # Read full contents and enforce 2 MB size limit
    full_contents = await file.read()
    if len(full_contents) > 2 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Logo file too large. Maximum 2MB.",
        )

    # Magic-byte validation — never trust client content_type
    detected = magic.from_buffer(full_contents[:2048], mime=True)
    if detected not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Only JPEG, PNG, GIF, and WebP images are allowed. Detected: {detected}",
        )

    # Strip EXIF metadata before storage
    try:
        img = Image.open(io.BytesIO(full_contents))
        clean_buf = io.BytesIO()
        img.save(clean_buf, format=img.format or "PNG")
        clean_bytes = clean_buf.getvalue()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not process the uploaded image. Please ensure it is a valid image file.",
        )

    # Encode to base64 data-URL — stored directly in DB, zero file-system dependency
    b64 = base64.b64encode(clean_bytes).decode("utf-8")
    data_url = f"data:{detected};base64,{b64}"

    # Update tenant
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one()
    tenant.logo_url = data_url
    await db.commit()
    await db.refresh(tenant)

    return TenantResponse.model_validate(tenant)


@router.get("/subscription", summary="Get subscription info")
async def get_subscription(
    db: DBSession,
    tenant_id: TenantID,
    current_user: CurrentUser,
):
    """Get current subscription plan details."""
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one()

    return {
        "plan": tenant.subscription_plan,
        "expires_at": tenant.subscription_expires_at,
        "is_active": tenant.is_active,
        "available_plans": [
            {
                "name": "free",
                "price": 0,
                "features": ["Up to 50 patients", "Basic billing", "1 staff user"],
            },
            {
                "name": "basic",
                "price": 999,
                "features": ["Up to 500 patients", "PDF receipts", "5 staff users", "Email notifications"],
            },
            {
                "name": "premium",
                "price": 2499,
                "features": ["Unlimited patients", "PDF receipts", "Unlimited staff", "Email notifications", "Analytics dashboard", "Priority support"],
            },
        ],
    }
