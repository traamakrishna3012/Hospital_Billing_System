"""
Report export routes — CSV and PDF.
"""

from __future__ import annotations

import csv
import io
from datetime import datetime, timezone

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.deps import CurrentUser, DBSession, TenantID
from app.models.bill import Bill

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/export/csv", summary="Export bills as CSV")
async def export_bills_csv(
    db: DBSession,
    tenant_id: TenantID,
    current_user: CurrentUser,
    status_filter: str = Query("", alias="status", max_length=20),
    date_from: str = Query("", max_length=10),
    date_to: str = Query("", max_length=10),
):
    """Export bills as a CSV file with optional date and status filters."""
    query = (
        select(Bill)
        .options(selectinload(Bill.patient), selectinload(Bill.doctor))
        .where(Bill.tenant_id == tenant_id)
    )

    if status_filter:
        query = query.where(Bill.status == status_filter)

    if date_from:
        try:
            from_date = datetime.strptime(date_from, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            query = query.where(Bill.created_at >= from_date)
        except ValueError:
            pass

    if date_to:
        try:
            to_date = datetime.strptime(date_to, "%Y-%m-%d").replace(
                hour=23, minute=59, second=59, tzinfo=timezone.utc
            )
            query = query.where(Bill.created_at <= to_date)
        except ValueError:
            pass

    result = await db.execute(query.order_by(Bill.created_at.desc()))
    bills = result.scalars().unique().all()

    # Build CSV
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Bill Number",
        "Date",
        "Patient Name",
        "Patient Phone",
        "Doctor Name",
        "Subtotal",
        "Tax %",
        "Tax Amount",
        "Discount %",
        "Discount Amount",
        "Total",
        "Status",
        "Payment Mode",
    ])

    _INJECTION_PREFIXES = ("=", "+", "-", "@", "\t", "\r")

    def _sanitize_csv(val: str) -> str:
        """Neutralize spreadsheet formula injection in exported CSV fields."""
        if isinstance(val, str) and val.startswith(_INJECTION_PREFIXES):
            return "'" + val
        return val

    for bill in bills:
        writer.writerow([
            _sanitize_csv(bill.bill_number or ""),
            bill.created_at.strftime("%Y-%m-%d %H:%M") if bill.created_at else "",
            _sanitize_csv(bill.patient.name if bill.patient else "N/A"),
            _sanitize_csv(bill.patient.phone if bill.patient else "N/A"),
            _sanitize_csv(bill.doctor.name if bill.doctor else "N/A"),
            float(bill.subtotal),
            float(bill.tax_percent),
            float(bill.tax_amount),
            float(bill.discount_percent),
            float(bill.discount_amount),
            float(bill.total),
            _sanitize_csv(bill.status or ""),
            _sanitize_csv(bill.payment_mode or ""),
        ])

    output.seek(0)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="bills_report_{timestamp}.csv"'
        },
    )
