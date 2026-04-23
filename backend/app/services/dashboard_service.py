"""
Dashboard analytics service — revenue and statistics aggregation.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select, func, and_, case, extract
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bill import Bill
from app.models.patient import Patient
from app.models.doctor import Doctor
from app.schemas.schemas import DashboardStats, RevenueChartData, RecentTransaction


async def get_dashboard_stats(db: AsyncSession, tenant_id: UUID | None) -> DashboardStats:
    """Get aggregate statistics for the dashboard."""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Base queries
    q1 = select(func.coalesce(func.sum(Bill.total), 0)).where(Bill.status == "paid")
    q2 = select(func.coalesce(func.sum(Bill.total), 0)).where(Bill.status == "paid", Bill.created_at >= today_start)
    q3 = select(func.coalesce(func.sum(Bill.total), 0)).where(Bill.status == "paid", Bill.created_at >= month_start)
    q4 = select(func.count(Patient.id))
    q5 = select(func.count(Bill.id))
    q6 = select(func.count(Bill.id)).where(Bill.created_at >= today_start)
    q7 = select(func.count(Bill.id)).where(Bill.created_at >= month_start)
    q8 = select(func.count(Doctor.id)).where(Doctor.is_active == True)

    # Apply tenant filter if not superadmin
    if tenant_id:
        q1 = q1.where(Bill.tenant_id == tenant_id)
        q2 = q2.where(Bill.tenant_id == tenant_id)
        q3 = q3.where(Bill.tenant_id == tenant_id)
        q4 = q4.where(Patient.tenant_id == tenant_id)
        q5 = q5.where(Bill.tenant_id == tenant_id)
        q6 = q6.where(Bill.tenant_id == tenant_id)
        q7 = q7.where(Bill.tenant_id == tenant_id)
        q8 = q8.where(Doctor.tenant_id == tenant_id)

    # Execute sequentially to prevent AsyncSession concurrent transaction corruption
    t1 = await db.execute(q1)
    t2 = await db.execute(q2)
    t3 = await db.execute(q3)
    t4 = await db.execute(q4)
    t5 = await db.execute(q5)
    t6 = await db.execute(q6)
    t7 = await db.execute(q7)
    t8 = await db.execute(q8)


    total_revenue = float(t1.scalar() or 0)
    today_revenue = float(t2.scalar() or 0)
    month_revenue = float(t3.scalar() or 0)
    total_patients = t4.scalar() or 0
    total_bills = t5.scalar() or 0
    today_bills = t6.scalar() or 0
    month_bills = t7.scalar() or 0
    total_doctors = t8.scalar() or 0

    return DashboardStats(
        total_revenue=total_revenue,
        total_patients=total_patients,
        total_bills=total_bills,
        total_doctors=total_doctors,
        today_revenue=today_revenue,
        today_bills=today_bills,
        month_revenue=month_revenue,
        month_bills=month_bills,
    )


async def get_revenue_chart_data(
    db: AsyncSession,
    tenant_id: UUID | None,
    period: str = "daily",  # daily | weekly | monthly
    days: int = 30,
) -> list[RevenueChartData]:
    """Get time-series revenue data for charts."""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    start_date = now - timedelta(days=days)
    if period == "monthly":
        stmt = (
            select(
                func.to_char(Bill.created_at, "YYYY-MM").label("period"),
                func.coalesce(func.sum(Bill.total), 0).label("revenue"),
                func.count(Bill.id).label("count"),
            )
            .where(Bill.status == "paid", Bill.created_at >= start_date)
            .group_by(func.to_char(Bill.created_at, "YYYY-MM"))
            .order_by(func.to_char(Bill.created_at, "YYYY-MM"))
        )
    elif period == "weekly":
        stmt = (
            select(
                func.to_char(Bill.created_at, "IYYY-IW").label("period"),
                func.coalesce(func.sum(Bill.total), 0).label("revenue"),
                func.count(Bill.id).label("count"),
            )
            .where(Bill.status == "paid", Bill.created_at >= start_date)
            .group_by(func.to_char(Bill.created_at, "IYYY-IW"))
            .order_by(func.to_char(Bill.created_at, "IYYY-IW"))
        )
    else:
        stmt = (
            select(
                func.to_char(Bill.created_at, "YYYY-MM-DD").label("period"),
                func.coalesce(func.sum(Bill.total), 0).label("revenue"),
                func.count(Bill.id).label("count"),
            )
            .where(Bill.status == "paid", Bill.created_at >= start_date)
            .group_by(func.to_char(Bill.created_at, "YYYY-MM-DD"))
            .order_by(func.to_char(Bill.created_at, "YYYY-MM-DD"))
        )

    if tenant_id:
        stmt = stmt.where(Bill.tenant_id == tenant_id)

    result = await db.execute(stmt)


    rows = result.all()
    return [
        RevenueChartData(label=row.period, revenue=float(row.revenue), count=row.count)
        for row in rows
    ]


async def get_recent_transactions(
    db: AsyncSession,
    tenant_id: UUID | None,
    limit: int = 10,
) -> list[RecentTransaction]:
    """Get recent bills for the dashboard."""
    from sqlalchemy.orm import selectinload
    stmt = (
        select(Bill)
        .options(selectinload(Bill.patient))
        .order_by(Bill.created_at.desc())
        .limit(limit)
    )
    if tenant_id:
        stmt = stmt.where(Bill.tenant_id == tenant_id)
    
    result = await db.execute(stmt)
    bills = result.scalars().all()

    transactions = []
    for bill in bills:
        # Get patient name
        patient = bill.patient
        patient_name = patient.name if patient else "Unknown"

        transactions.append(RecentTransaction(
            id=bill.id,
            bill_number=bill.bill_number,
            patient_name=patient_name,
            total=float(bill.total),
            status=bill.status,
            payment_mode=bill.payment_mode,
            created_at=bill.created_at,
        ))

    return transactions
