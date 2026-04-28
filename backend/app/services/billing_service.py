"""
Billing service — handles bill creation, auto-numbering, and financial calculations.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bill import Bill, BillItem
from app.models.test import MedicalTest
from app.models.tenant import Tenant
from app.schemas.schemas import BillCreate


async def generate_bill_number(db: AsyncSession, tenant_id: UUID) -> str:
    """
    Generate unique bill number: INV-YYYYMMDD-XXXX
    Auto-increments the sequence number per day per tenant.
    """
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    prefix = f"INV-{today}-"

    # Find the last bill number for this tenant today
    result = await db.execute(
        select(Bill.bill_number)
        .where(Bill.tenant_id == tenant_id, Bill.bill_number.like(f"{prefix}%"))
        .order_by(Bill.bill_number.desc())
        .limit(1)
    )
    last_number = result.scalar_one_or_none()

    if last_number:
        seq = int(last_number.split("-")[-1]) + 1
    else:
        seq = 1

    return f"{prefix}{seq:04d}"


def calculate_bill_totals(
    items: list[dict],
    tax_percent: float,
    discount_percent: float,
) -> dict:
    """
    Calculate subtotal, tax, discount, and total for a bill.
    Returns dict with all calculated financial fields.
    """
    subtotal = sum(item["unit_price"] * item["quantity"] for item in items)

    # Discount applied on subtotal
    discount_amount = round(subtotal * (discount_percent / 100), 2)
    after_discount = subtotal - discount_amount

    # Tax applied after discount
    tax_amount = round(after_discount * (tax_percent / 100), 2)
    total = round(after_discount + tax_amount, 2)

    return {
        "subtotal": round(subtotal, 2),
        "tax_percent": tax_percent,
        "tax_amount": tax_amount,
        "discount_percent": discount_percent,
        "discount_amount": discount_amount,
        "total": total,
    }


async def create_bill(
    db: AsyncSession,
    tenant_id: UUID,
    data: BillCreate,
    default_tax_percent: float = 18.0,
) -> Bill:
    """Create a bill with items and auto-calculated totals."""
    bill_number = await generate_bill_number(db, tenant_id)
    tax_pct = data.tax_percent if data.tax_percent is not None else default_tax_percent
    discount_pct = data.discount_percent if data.discount_percent is not None else 0.0

    # Prepare item dicts for calculation
    item_dicts = [
        {"unit_price": item.unit_price, "quantity": item.quantity}
        for item in data.items
    ]
    totals = calculate_bill_totals(item_dicts, tax_pct, discount_pct)

    # Create bill
    bill = Bill(
        tenant_id=tenant_id,
        bill_number=bill_number,
        patient_id=data.patient_id,
        doctor_id=data.doctor_id,
        status=data.status,
        notes=data.notes,
        payment_mode=data.payment_mode,
        transaction_id=data.transaction_id,
        **totals,
    )
    db.add(bill)
    await db.flush()  # get bill.id

    # Create bill items
    for item_data in data.items:
        item_total = round(item_data.unit_price * item_data.quantity, 2)

        # Resolve code: use provided code first, then look up from the test
        item_code = item_data.code or None
        if not item_code and item_data.medical_test_id:
            test_result = await db.execute(
                select(MedicalTest).where(MedicalTest.id == item_data.medical_test_id)
            )
            test = test_result.scalar_one_or_none()
            if test:
                item_code = test.code

        bill_item = BillItem(
            bill_id=bill.id,
            medical_test_id=item_data.medical_test_id,
            code=item_code,
            description=item_data.description,
            quantity=item_data.quantity,
            unit_price=float(item_data.unit_price),
            total=item_total,
        )
        db.add(bill_item)

    await db.commit()
    await db.refresh(bill)
    return bill


async def recalculate_bill(bill: Bill, db: AsyncSession) -> Bill:
    """Recalculate bill totals after item or discount changes."""
    item_dicts = [
        {"unit_price": float(item.unit_price), "quantity": item.quantity}
        for item in bill.items
    ]
    totals = calculate_bill_totals(
        item_dicts,
        float(bill.tax_percent),
        float(bill.discount_percent),
    )

    for key, value in totals.items():
        setattr(bill, key, value)

    await db.commit()
    await db.refresh(bill)
    return bill
