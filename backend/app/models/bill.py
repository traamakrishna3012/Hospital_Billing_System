"""Bill & BillItem models — invoicing with auto-calculation."""

from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import ForeignKey, String, Integer, Numeric, Text, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Bill(Base):
    __tablename__ = "bills"

    # ── Tenant Isolation ──────────────────────────────────────
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Bill Identity ─────────────────────────────────────────
    bill_number: Mapped[str] = mapped_column(String(30), nullable=False, unique=True)

    # ── References ────────────────────────────────────────────
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("patients.id", ondelete="RESTRICT"),
        nullable=False,
    )
    doctor_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("doctors.id", ondelete="SET NULL"),
        nullable=True,
    )

    # ── Financials ────────────────────────────────────────────
    subtotal: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    tax_percent: Mapped[float] = mapped_column(Numeric(5, 2), default=18.0)
    tax_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    discount_percent: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    discount_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    total: Mapped[float] = mapped_column(Numeric(12, 2), default=0)

    # ── Meta ──────────────────────────────────────────────────
    status: Mapped[str] = mapped_column(
        String(20), default="paid", server_default="paid"
    )  # paid | unpaid | cancelled
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    pdf_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    payment_mode: Mapped[str] = mapped_column(
        String(20), default="cash", server_default="cash"
    )  # cash | card | upi | online
    transaction_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # ── Relationships ─────────────────────────────────────────
    items: Mapped[list["BillItem"]] = relationship(
        "BillItem", back_populates="bill", cascade="all, delete-orphan"
    )
    patient: Mapped["Patient"] = relationship("Patient", lazy="selectin")  # noqa: F821
    doctor: Mapped[Optional["Doctor"]] = relationship("Doctor", lazy="selectin")  # noqa: F821

    __table_args__ = (
        Index("ix_bills_tenant_created", "tenant_id", "created_at"),
        Index("ix_bills_tenant_patient", "tenant_id", "patient_id"),
        Index("ix_bills_tenant_bill_number", "tenant_id", "bill_number"),
    )

    def __repr__(self) -> str:
        return f"<Bill {self.bill_number} total=₹{self.total}>"


class BillItem(Base):
    __tablename__ = "bill_items"

    # ── Parent Bill ───────────────────────────────────────────
    bill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("bills.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Reference to Test (optional — for custom line items) ─
    medical_test_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("medical_tests.id", ondelete="SET NULL"),
        nullable=True,
    )

    # ── Item Details ──────────────────────────────────────────
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # copied from MedicalTest.code
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    unit_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    total: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)

    # ── Relationships ─────────────────────────────────────────
    bill: Mapped["Bill"] = relationship("Bill", back_populates="items")

    def __repr__(self) -> str:
        return f"<BillItem {self.description} qty={self.quantity}>"
