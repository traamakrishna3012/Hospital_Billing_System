"""
Billing routes — create, list, detail, PDF download.
"""

from __future__ import annotations

import os
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, status
from fastapi.responses import FileResponse, Response
from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload

from app.core.deps import CurrentUser, DBSession, TenantID
from app.models.bill import Bill, BillItem
from app.models.patient import Patient
from app.models.tenant import Tenant
from app.schemas.schemas import (
    BillCreate,
    BillResponse,
    BillUpdate,
    PaginatedResponse,
)
from app.services.billing_service import create_bill, recalculate_bill
from app.services.pdf_service import generate_receipt_pdf
from app.services.email_service import send_bill_receipt_email
from app.core.config import get_settings

settings = get_settings()

router = APIRouter(prefix="/bills", tags=["Billing"])


@router.get("", response_model=PaginatedResponse, summary="List bills")
async def list_bills(
    db: DBSession,
    tenant_id: TenantID,
    current_user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str = Query("", max_length=100),
    status_filter: str = Query("", alias="status", max_length=20),
    payment_mode: str = Query("", max_length=20),
):
    """List bills with search, status filter, and pagination."""
    query = (
        select(Bill)
        .options(selectinload(Bill.items), selectinload(Bill.patient), selectinload(Bill.doctor))
        .where(Bill.tenant_id == tenant_id)
    )
    count_query = select(func.count(Bill.id)).where(Bill.tenant_id == tenant_id)

    if search:
        # Search by bill number or patient name (via subquery)
        patient_ids = select(Patient.id).where(
            Patient.tenant_id == tenant_id,
            Patient.name.ilike(f"%{search}%"),
        )
        search_filter = or_(
            Bill.bill_number.ilike(f"%{search}%"),
            Bill.patient_id.in_(patient_ids),
        )
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)

    if status_filter:
        query = query.where(Bill.status == status_filter)
        count_query = count_query.where(Bill.status == status_filter)

    if payment_mode:
        query = query.where(Bill.payment_mode == payment_mode)
        count_query = count_query.where(Bill.payment_mode == payment_mode)

    total = (await db.execute(count_query)).scalar() or 0
    total_pages = max(1, (total + page_size - 1) // page_size)

    offset = (page - 1) * page_size
    result = await db.execute(
        query.order_by(Bill.created_at.desc()).offset(offset).limit(page_size)
    )
    bills = result.scalars().unique().all()

    return PaginatedResponse(
        items=[BillResponse.model_validate(b) for b in bills],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/{bill_id}", response_model=BillResponse, summary="Get bill details")
async def get_bill(
    bill_id: UUID,
    db: DBSession,
    tenant_id: TenantID,
    current_user: CurrentUser,
):
    result = await db.execute(
        select(Bill)
        .options(selectinload(Bill.items), selectinload(Bill.patient), selectinload(Bill.doctor))
        .where(Bill.id == bill_id, Bill.tenant_id == tenant_id)
    )
    bill = result.scalar_one_or_none()
    if not bill:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bill not found")
    return BillResponse.model_validate(bill)


@router.post("", response_model=BillResponse, status_code=status.HTTP_201_CREATED, summary="Create bill")
async def create_new_bill(
    data: BillCreate,
    db: DBSession,
    tenant_id: TenantID,
    current_user: CurrentUser,
):
    """Create a new bill with items. Auto-calculates totals, tax, and discount."""
    # Verify patient belongs to tenant
    patient_result = await db.execute(
        select(Patient).where(Patient.id == data.patient_id, Patient.tenant_id == tenant_id)
    )
    if not patient_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")

    # Get tenant for default tax
    tenant = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant_obj = tenant.scalar_one()

    bill = await create_bill(db, tenant_id, data, default_tax_percent=tenant_obj.tax_percent)

    # Reload with relationships
    result = await db.execute(
        select(Bill)
        .options(selectinload(Bill.items), selectinload(Bill.patient), selectinload(Bill.doctor))
        .where(Bill.id == bill.id)
    )
    bill = result.scalar_one()
    return BillResponse.model_validate(bill)


@router.put("/{bill_id}", response_model=BillResponse, summary="Update bill")
async def update_bill(
    bill_id: UUID,
    data: BillUpdate,
    db: DBSession,
    tenant_id: TenantID,
    current_user: CurrentUser,
):
    result = await db.execute(
        select(Bill)
        .options(selectinload(Bill.items))
        .where(Bill.id == bill_id, Bill.tenant_id == tenant_id)
    )
    bill = result.scalar_one_or_none()
    if not bill:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bill not found")

    update_data = data.model_dump(exclude_unset=True)
    needs_recalc = "discount_percent" in update_data

    for key, value in update_data.items():
        setattr(bill, key, value)

    if needs_recalc:
        bill = await recalculate_bill(bill, db)
    else:
        await db.commit()
        await db.refresh(bill)

    return BillResponse.model_validate(bill)


@router.delete("/{bill_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete bill")
async def delete_bill(
    bill_id: UUID,
    db: DBSession,
    tenant_id: TenantID,
    current_user: CurrentUser,
):
    result = await db.execute(
        select(Bill).where(Bill.id == bill_id, Bill.tenant_id == tenant_id)
    )
    bill = result.scalar_one_or_none()
    if not bill:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bill not found")

    await db.delete(bill)
    await db.commit()


@router.get("/{bill_id}/pdf", summary="Download bill as PDF")
async def download_bill_pdf(
    bill_id: UUID,
    db: DBSession,
    tenant_id: TenantID,
    current_user: CurrentUser,
):
    """Generate and download a PDF receipt for a bill."""
    # Load bill with relationships
    result = await db.execute(
        select(Bill)
        .options(selectinload(Bill.items), selectinload(Bill.patient), selectinload(Bill.doctor))
        .where(Bill.id == bill_id, Bill.tenant_id == tenant_id)
    )
    bill = result.scalar_one_or_none()
    if not bill:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bill not found")

    # Load tenant info
    tenant_result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = tenant_result.scalar_one()

    # Prepare data dicts
    bill_data = {
        "bill_number": bill.bill_number,
        "subtotal": float(bill.subtotal),
        "tax_percent": float(bill.tax_percent),
        "tax_amount": float(bill.tax_amount),
        "discount_percent": float(bill.discount_percent),
        "discount_amount": float(bill.discount_amount),
        "total": float(bill.total),
        "status": bill.status,
        "payment_mode": bill.payment_mode,
        "notes": bill.notes,
        "created_at": bill.created_at,
    }
    tenant_data = {
        "name": tenant.name,
        "email": tenant.email,
        "phone": tenant.phone,
        "address": tenant.address,
        "city": tenant.city,
        "state": tenant.state,
        "pincode": tenant.pincode,
        "logo_url": tenant.logo_url,
        "tagline": tenant.tagline,
        "currency": tenant.currency,
    }
    patient_data = {
        "name":    bill.patient.name    if bill.patient else "N/A",
        "phone":   bill.patient.phone   if bill.patient else "N/A",
        "email":   bill.patient.email   if bill.patient else None,
        "address": bill.patient.address if bill.patient else None,
        "age":     bill.patient.age     if bill.patient else "N/A",
        "gender":  bill.patient.gender  if bill.patient else "N/A",
    }
    doctor_data = None
    if bill.doctor:
        doctor_data = {
            "name": bill.doctor.name,
            "specialization": bill.doctor.specialization,
        }
    items_data = [
        {
            "description": item.description,
            "code": item.code or "",
            "quantity": item.quantity,
            "unit_price": float(item.unit_price),
            "total": float(item.total),
        }
        for item in bill.items
    ]

    # Generate PDF
    pdf_path = os.path.join(
        settings.UPLOAD_DIR, "receipts", str(tenant_id), f"{bill.bill_number}.pdf"
    )
    pdf_bytes = generate_receipt_pdf(
        bill_data, tenant_data, patient_data, doctor_data, items_data, pdf_path
    )

    # Update bill with PDF URL
    bill.pdf_url = pdf_path
    await db.commit()

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{bill.bill_number}.pdf"'
        },
    )


@router.post("/{bill_id}/send-email", summary="Email bill receipt to patient")
async def email_bill_receipt(
    bill_id: UUID,
    db: DBSession,
    tenant_id: TenantID,
    current_user: CurrentUser,
    background_tasks: BackgroundTasks,
):
    """Generate PDF and email receipt to the patient."""
    # Load bill
    result = await db.execute(
        select(Bill)
        .options(selectinload(Bill.items), selectinload(Bill.patient), selectinload(Bill.doctor))
        .where(Bill.id == bill_id, Bill.tenant_id == tenant_id)
    )
    bill = result.scalar_one_or_none()
    if not bill:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bill not found")

    # Load patient explicitly to verify email
    from app.models.patient import Patient
    patient_result = await db.execute(
        select(Patient).where(Patient.id == bill.patient_id, Patient.tenant_id == tenant_id)
    )
    patient = patient_result.scalar_one_or_none()

    if not patient or not patient.email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Patient has no registered email address."
        )
    
    # Securely override recipient with the verified patient email
    recipient_email = patient.email

    # Load tenant
    tenant_result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = tenant_result.scalar_one()


    # Generate PDF
    bill_data = {
        "bill_number": bill.bill_number,
        "subtotal": float(bill.subtotal),
        "tax_percent": float(bill.tax_percent),
        "tax_amount": float(bill.tax_amount),
        "discount_percent": float(bill.discount_percent),
        "discount_amount": float(bill.discount_amount),
        "total": float(bill.total),
        "status": bill.status,
        "payment_mode": bill.payment_mode,
        "notes": bill.notes,
        "created_at": bill.created_at,
    }
    tenant_data = {
        "name": tenant.name,
        "email": tenant.email,
        "phone": tenant.phone,
        "address": tenant.address,
        "city": tenant.city,
        "state": tenant.state,
        "pincode": tenant.pincode,
        "logo_url": tenant.logo_url,
        "tagline": tenant.tagline,
        "currency": tenant.currency,
    }
    patient_data = {
        "name":    bill.patient.name,
        "phone":   bill.patient.phone,
        "email":   bill.patient.email,
        "address": bill.patient.address,
        "age":     bill.patient.age,
        "gender":  bill.patient.gender,
    }
    doctor_data = None
    if bill.doctor:
        doctor_data = {
            "name": bill.doctor.name,
            "specialization": bill.doctor.specialization,
        }
    items_data = [
        {
            "description": item.description,
            "code": item.code or "",
            "quantity": item.quantity,
            "unit_price": float(item.unit_price),
            "total": float(item.total),
        }
        for item in bill.items
    ]

    pdf_bytes = generate_receipt_pdf(
        bill_data, tenant_data, patient_data, doctor_data, items_data
    )

    # Send email
    background_tasks.add_task(
        send_bill_receipt_email,
        patient_email=recipient_email,
        patient_name=patient.name,
        clinic_name=tenant.name,
        bill_number=bill.bill_number,
        total=float(bill.total),
        currency=tenant.currency,
        pdf_bytes=pdf_bytes,
    )

    return {"message": "Receipt email has been queued for delivery", "email": recipient_email}



@router.get("/{bill_id}/file", summary="Serve bill PDF securely")
async def serve_bill_pdf(
    bill_id: UUID,
    db: DBSession,
    tenant_id: TenantID,
    current_user: CurrentUser,
):
    """Serve a bill's PDF file through an authenticated endpoint (no public static mount)."""
    result = await db.execute(
        select(Bill).where(Bill.id == bill_id, Bill.tenant_id == tenant_id)
    )
    bill = result.scalar_one_or_none()
    if not bill or not bill.pdf_url:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PDF not found")

    # Path traversal protection
    safe_path = Path(bill.pdf_url).resolve()
    allowed_dir = Path(settings.UPLOAD_DIR).resolve()
    if not str(safe_path).startswith(str(allowed_dir)):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    if not safe_path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PDF file not found on disk")

    return FileResponse(safe_path, media_type="application/pdf")
