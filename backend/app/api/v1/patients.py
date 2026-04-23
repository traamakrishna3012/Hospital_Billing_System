"""
Patient management routes — CRUD with tenant isolation.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentUser, DBSession, TenantID
from app.models.patient import Patient
from app.schemas.schemas import (
    PaginatedResponse,
    PatientCreate,
    PatientResponse,
    PatientUpdate,
)

router = APIRouter(prefix="/patients", tags=["Patients"])


@router.get("", response_model=PaginatedResponse, summary="List patients")
async def list_patients(
    db: DBSession,
    tenant_id: TenantID,
    current_user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str = Query("", max_length=100),
    gender: str = Query("", max_length=10),
):
    """List patients with search, filters, and pagination."""
    query = select(Patient)
    count_query = select(func.count(Patient.id))

    if tenant_id:
        query = query.where(Patient.tenant_id == tenant_id)
        count_query = count_query.where(Patient.tenant_id == tenant_id)


    # Search by name or phone
    if search:
        search_filter = or_(
            Patient.name.ilike(f"%{search}%"),
            Patient.phone.ilike(f"%{search}%"),
        )
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)

    # Filter by gender
    if gender:
        query = query.where(Patient.gender == gender)
        count_query = count_query.where(Patient.gender == gender)

    # Get total count
    total = (await db.execute(count_query)).scalar() or 0
    total_pages = max(1, (total + page_size - 1) // page_size)

    # Paginate
    offset = (page - 1) * page_size
    result = await db.execute(
        query.order_by(Patient.created_at.desc()).offset(offset).limit(page_size)
    )
    patients = result.scalars().all()

    return PaginatedResponse(
        items=[PatientResponse.model_validate(p) for p in patients],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/{patient_id}", response_model=PatientResponse, summary="Get patient details")
async def get_patient(
    patient_id: UUID,
    db: DBSession,
    tenant_id: TenantID,
    current_user: CurrentUser,
):
    """Get a specific patient's details."""
    result = await db.execute(
        select(Patient).where(Patient.id == patient_id, Patient.tenant_id == tenant_id)
    )
    patient = result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    return PatientResponse.model_validate(patient)


@router.post("", response_model=PatientResponse, status_code=status.HTTP_201_CREATED, summary="Create patient")
async def create_patient(
    data: PatientCreate,
    db: DBSession,
    tenant_id: TenantID,
    current_user: CurrentUser,
):
    """Create a new patient record."""
    patient = Patient(tenant_id=tenant_id, **data.model_dump())
    db.add(patient)
    await db.commit()
    await db.refresh(patient)
    return PatientResponse.model_validate(patient)


@router.put("/{patient_id}", response_model=PatientResponse, summary="Update patient")
async def update_patient(
    patient_id: UUID,
    data: PatientUpdate,
    db: DBSession,
    tenant_id: TenantID,
    current_user: CurrentUser,
):
    """Update a patient's details. Only non-null fields are updated."""
    result = await db.execute(
        select(Patient).where(Patient.id == patient_id, Patient.tenant_id == tenant_id)
    )
    patient = result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(patient, key, value)

    await db.commit()
    await db.refresh(patient)
    return PatientResponse.model_validate(patient)


@router.delete("/{patient_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete patient")
async def delete_patient(
    patient_id: UUID,
    db: DBSession,
    tenant_id: TenantID,
    current_user: CurrentUser,
):
    """Delete a patient record."""
    result = await db.execute(
        select(Patient).where(Patient.id == patient_id, Patient.tenant_id == tenant_id)
    )
    patient = result.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")

    await db.delete(patient)
    await db.commit()
