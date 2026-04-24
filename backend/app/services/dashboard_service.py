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
    """Get aggregate statistics for the dashboard in a single pass for speed."""
    try:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        # 1. Revenue & Bill Stats (Single scan of Bill table)
        bill_stmt = select(
            func.coalesce(func.sum(case((Bill.status == "paid", Bill.total), else_=0)), 0).label("total_revenue"),
            func.coalesce(func.sum(case((and_(Bill.status == "paid", Bill.created_at >= today_start), Bill.total), else_=0)), 0).label("today_revenue"),
            func.coalesce(func.sum(case((and_(Bill.status == "paid", Bill.created_at >= month_start), Bill.total), else_=0)), 0).label("month_revenue"),
            func.count(Bill.id).label("total_bills"),
            func.count(case((Bill.created_at >= today_start, Bill.id))).label("today_bills"),
            func.count(case((Bill.created_at >= month_start, Bill.id))).label("month_bills")
        )
        
        # 2. Patient Stats
        patient_stmt = select(func.count(Patient.id)).label("total_patients")
        
        # 3. Doctor Stats
        doctor_stmt = select(func.count(Doctor.id)).where(Doctor.is_active == True).label("total_doctors")

        if tenant_id:
            bill_stmt = bill_stmt.where(Bill.tenant_id == tenant_id)
            patient_stmt = select(func.count(Patient.id)).where(Patient.tenant_id == tenant_id)
            doctor_stmt = select(func.count(Doctor.id)).where(Doctor.tenant_id == tenant_id, Doctor.is_active == True)

        # Combine into one mega query result
        res_bills = await db.execute(bill_stmt)
        row_bills = res_bills.mappings().one()
        
        res_patients = await db.execute(patient_stmt)
        res_doctors = await db.execute(doctor_stmt)

        return DashboardStats(
            total_revenue=float(row_bills["total_revenue"] or 0),
            today_revenue=float(row_bills["today_revenue"] or 0),
            month_revenue=float(row_bills["month_revenue"] or 0),
            total_bills=row_bills["total_bills"] or 0,
            today_bills=row_bills["today_bills"] or 0,
            month_bills=row_bills["month_bills"] or 0,
            total_patients=res_patients.scalar() or 0,
            total_doctors=res_doctors.scalar() or 0,
        )
    except Exception as e:
        from loguru import logger
        logger.error(f"Dashboard Stats Error: {e}")
        # Return empty stats instead of crashing 500
        return DashboardStats(
            total_revenue=0.0, total_patients=0, total_bills=0, total_doctors=0,
            today_revenue=0.0, today_bills=0, month_revenue=0.0, month_bills=0
        )





async def get_revenue_chart_data(
    db: AsyncSession,
    tenant_id: UUID | None,
    period: str = "daily",  # daily | weekly | monthly
    days: int = 30,
) -> list[RevenueChartData]:
    """Get time-series revenue data for charts with fail-safe date truncation."""
    try:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        start_date = now - timedelta(days=days)
        
        # Use date_trunc for more robust grouping in PostgreSQL
        if period == "monthly":
            trunc_level = "month"
            date_format = "YYYY-MM"
        elif period == "weekly":
            trunc_level = "week"
            date_format = "IYYY-IW"
        else:
            trunc_level = "day"
            date_format = "YYYY-MM-DD"

        stmt = (
            select(
                func.to_char(func.date_trunc(trunc_level, Bill.created_at), date_format).label("period"),
                func.coalesce(func.sum(Bill.total), 0).label("revenue"),
                func.count(Bill.id).label("count"),
            )
            .where(func.lower(Bill.status) == "paid")
            .where(Bill.created_at >= start_date)
            .group_by(func.date_trunc(trunc_level, Bill.created_at))
            .order_by(func.date_trunc(trunc_level, Bill.created_at))
        )

        if tenant_id:
            stmt = stmt.where(Bill.tenant_id == tenant_id)

        result = await db.execute(stmt)
        rows = result.mappings().all()

        return [
            RevenueChartData(
                label=row["period"], 
                revenue=float(row["revenue"] or 0), 
                count=row["count"] or 0
            )
            for row in rows
        ]
    except Exception as e:
        from loguru import logger
        logger.error(f"Dashboard Chart Error: {e}")
        return []





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
