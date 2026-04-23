"""
Doctor management routes — CRUD with tenant isolation.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select, func, or_

from app.core.deps import CurrentUser, DBSession, TenantID
from app.models.doctor import Doctor
from app.schemas.schemas import (
    DoctorCreate,
    DoctorResponse,
    DoctorUpdate,
    PaginatedResponse,
)

router = APIRouter(prefix="/doctors", tags=["Doctors"])


@router.get("", response_model=PaginatedResponse, summary="List doctors")
async def list_doctors(
    db: DBSession,
    tenant_id: TenantID,
    current_user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str = Query("", max_length=100),
    specialization: str = Query("", max_length=100),
    active_only: bool = Query(True),
):
    """List doctors with search, specialization filter, and pagination."""
    query = select(Doctor)
    count_query = select(func.count(Doctor.id))

    if tenant_id:
        query = query.where(Doctor.tenant_id == tenant_id)
        count_query = count_query.where(Doctor.tenant_id == tenant_id)


    if active_only:
        query = query.where(Doctor.is_active == True)  # noqa: E712
        count_query = count_query.where(Doctor.is_active == True)  # noqa: E712

    if search:
        search_filter = or_(
            Doctor.name.ilike(f"%{search}%"),
            Doctor.specialization.ilike(f"%{search}%"),
        )
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)

    if specialization:
        query = query.where(Doctor.specialization.ilike(f"%{specialization}%"))
        count_query = count_query.where(Doctor.specialization.ilike(f"%{specialization}%"))

    total = (await db.execute(count_query)).scalar() or 0
    total_pages = max(1, (total + page_size - 1) // page_size)

    offset = (page - 1) * page_size
    result = await db.execute(
        query.order_by(Doctor.name).offset(offset).limit(page_size)
    )
    doctors = result.scalars().all()

    return PaginatedResponse(
        items=[DoctorResponse.model_validate(d) for d in doctors],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/{doctor_id}", response_model=DoctorResponse, summary="Get doctor details")
async def get_doctor(
    doctor_id: UUID,
    db: DBSession,
    tenant_id: TenantID,
    current_user: CurrentUser,
):
    result = await db.execute(
        select(Doctor).where(Doctor.id == doctor_id, Doctor.tenant_id == tenant_id)
    )
    doctor = result.scalar_one_or_none()
    if not doctor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found")
    return DoctorResponse.model_validate(doctor)


@router.post("", response_model=DoctorResponse, status_code=status.HTTP_201_CREATED, summary="Add doctor")
async def create_doctor(
    data: DoctorCreate,
    db: DBSession,
    tenant_id: TenantID,
    current_user: CurrentUser,
):
    doctor = Doctor(tenant_id=tenant_id, **data.model_dump())
    db.add(doctor)
    await db.commit()
    await db.refresh(doctor)
    return DoctorResponse.model_validate(doctor)


@router.put("/{doctor_id}", response_model=DoctorResponse, summary="Update doctor")
async def update_doctor(
    doctor_id: UUID,
    data: DoctorUpdate,
    db: DBSession,
    tenant_id: TenantID,
    current_user: CurrentUser,
):
    result = await db.execute(
        select(Doctor).where(Doctor.id == doctor_id, Doctor.tenant_id == tenant_id)
    )
    doctor = result.scalar_one_or_none()
    if not doctor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found")

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(doctor, key, value)

    await db.commit()
    await db.refresh(doctor)
    return DoctorResponse.model_validate(doctor)


@router.delete("/{doctor_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Remove doctor")
async def delete_doctor(
    doctor_id: UUID,
    db: DBSession,
    tenant_id: TenantID,
    current_user: CurrentUser,
):
    result = await db.execute(
        select(Doctor).where(Doctor.id == doctor_id, Doctor.tenant_id == tenant_id)
    )
    doctor = result.scalar_one_or_none()
    if not doctor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found")

    await db.delete(doctor)
    await db.commit()
