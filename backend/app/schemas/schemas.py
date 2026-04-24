"""
Pydantic schemas for request validation and response serialization.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator


# ═══════════════════════════════════════════════════════════════
# Auth Schemas
# ═══════════════════════════════════════════════════════════════

class RegisterRequest(BaseModel):
    """Clinic registration — creates tenant + admin user."""
    clinic_name: str = Field(..., min_length=2, max_length=255)
    clinic_email: EmailStr
    clinic_phone: str = Field(default="", max_length=20)
    clinic_address: str = Field(default="", max_length=1000)
    admin_name: str = Field(..., min_length=2, max_length=255)
    admin_email: EmailStr
    admin_password: str = Field(..., min_length=8, max_length=128)

    @field_validator("admin_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse  # forward ref resolved below


class RefreshRequest(BaseModel):
    refresh_token: Optional[str] = None


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v



# ═══════════════════════════════════════════════════════════════
# User Schemas
# ═══════════════════════════════════════════════════════════════

class UserResponse(BaseModel):
    id: UUID
    tenant_id: Optional[UUID] = None
    email: str
    full_name: str
    phone: Optional[str] = None
    role: str
    is_active: bool
    is_approved: bool = False
    modules: Optional[dict] = None          # per-user module overrides
    tenant_modules: Optional[dict] = None   # computed — used by Sidebar
    created_at: datetime

    model_config = {"from_attributes": True}


class UserCreateRequest(BaseModel):
    """Admin creating a staff user."""
    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=255)
    phone: str = Field(default="", max_length=20)
    password: str = Field(..., min_length=8, max_length=128)
    role: str = Field(default="staff", pattern="^(admin|staff|doctor)$")


class UserUpdateRequest(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=255)
    phone: Optional[str] = Field(None, max_length=20)
    role: Optional[str] = Field(None, pattern="^(admin|staff|doctor)$")
    is_active: Optional[bool] = None
    modules: Optional[dict] = None   # per-staff module access control


# ═══════════════════════════════════════════════════════════════
# Tenant / Clinic Schemas
# ═══════════════════════════════════════════════════════════════

class TenantResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    email: str
    phone: Optional[str] = None
    logo_url: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    website: Optional[str] = None
    tagline: Optional[str] = None
    subscription_plan: str
    tax_percent: float
    currency: str
    is_active: bool
    is_approved: bool
    biller_header: Optional[str] = None
    modules: Optional[dict] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class TenantUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=20)
    address: Optional[str] = Field(None, max_length=1000)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    pincode: Optional[str] = Field(None, max_length=10)
    website: Optional[str] = Field(None, max_length=255)
    tagline: Optional[str] = Field(None, max_length=500)
    tax_percent: Optional[float] = Field(None, ge=0, le=100)
    currency: Optional[str] = Field(None, max_length=5)
    biller_header: Optional[str] = None


# ═══════════════════════════════════════════════════════════════
# Patient Schemas
# ═══════════════════════════════════════════════════════════════

class PatientCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    age: int = Field(..., ge=0, le=150)
    gender: str = Field(..., pattern="^(male|female|other)$")
    phone: str = Field(..., min_length=5, max_length=20)
    email: Optional[EmailStr] = None
    address: Optional[str] = Field(None, max_length=1000)
    blood_group: Optional[str] = Field(None, max_length=5)
    medical_notes: Optional[str] = None


class PatientUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    age: Optional[int] = Field(None, ge=0, le=150)
    gender: Optional[str] = Field(None, pattern="^(male|female|other)$")
    phone: Optional[str] = Field(None, min_length=5, max_length=20)
    email: Optional[EmailStr] = None
    address: Optional[str] = Field(None, max_length=1000)
    blood_group: Optional[str] = Field(None, max_length=5)
    medical_notes: Optional[str] = None


class PatientResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    name: str
    age: int
    gender: str
    phone: str
    email: Optional[str] = None
    address: Optional[str] = None
    blood_group: Optional[str] = None
    medical_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ═══════════════════════════════════════════════════════════════
# Doctor Schemas
# ═══════════════════════════════════════════════════════════════

class DoctorCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    specialization: str = Field(..., min_length=1, max_length=255)
    qualification: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=20)
    email: Optional[EmailStr] = None
    consultation_fee: float = Field(..., ge=0)
    availability: Optional[str] = Field(None, max_length=1000)


class DoctorUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    specialization: Optional[str] = Field(None, min_length=1, max_length=255)
    qualification: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=20)
    email: Optional[EmailStr] = None
    consultation_fee: Optional[float] = Field(None, ge=0)
    availability: Optional[str] = Field(None, max_length=1000)
    is_active: Optional[bool] = None


class DoctorResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    name: str
    specialization: str
    qualification: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    consultation_fee: float
    availability: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ═══════════════════════════════════════════════════════════════
# Test & Category Schemas
# ═══════════════════════════════════════════════════════════════

class TestCategoryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None


class TestCategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None


class TestCategoryResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    name: str
    description: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class MedicalTestCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    price: float = Field(..., ge=0)
    code: Optional[str] = Field(None, max_length=50)
    category_id: Optional[UUID] = None


class MedicalTestUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    price: Optional[float] = Field(None, ge=0)
    code: Optional[str] = Field(None, max_length=50)
    category_id: Optional[UUID] = None
    is_active: Optional[bool] = None


class MedicalTestResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    category_id: Optional[UUID] = None
    name: str
    description: Optional[str] = None
    price: float
    code: Optional[str] = None
    is_active: bool
    category: Optional[TestCategoryResponse] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ═══════════════════════════════════════════════════════════════
# Billing Schemas
# ═══════════════════════════════════════════════════════════════

class BillItemCreate(BaseModel):
    medical_test_id: Optional[UUID] = None
    code: Optional[str] = None          # test code — sent from frontend, stored on item
    description: str = Field(..., min_length=1, max_length=500)
    quantity: int = Field(default=1, ge=1)
    unit_price: float = Field(..., ge=0)


class BillItemResponse(BaseModel):
    id: UUID
    bill_id: UUID
    medical_test_id: Optional[UUID] = None
    code: Optional[str] = None
    description: str
    quantity: int
    unit_price: float
    total: float
    created_at: datetime

    model_config = {"from_attributes": True}


class BillCreate(BaseModel):
    patient_id: UUID
    doctor_id: Optional[UUID] = None
    items: list[BillItemCreate] = Field(..., min_length=1)
    tax_percent: Optional[float] = Field(None, ge=0, le=100)
    discount_percent: Optional[float] = Field(None, ge=0, le=100)
    notes: Optional[str] = None
    payment_mode: str = Field(default="cash", pattern="^(cash|card|upi|online)$")
    status: str = Field(default="paid", pattern="^(paid|unpaid|cancelled)$")


class BillUpdate(BaseModel):
    status: Optional[str] = Field(None, pattern="^(paid|unpaid|cancelled)$")
    notes: Optional[str] = None
    payment_mode: Optional[str] = Field(None, pattern="^(cash|card|upi|online)$")
    discount_percent: Optional[float] = Field(None, ge=0, le=100)


class BillResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    bill_number: str
    patient_id: UUID
    doctor_id: Optional[UUID] = None
    subtotal: float
    tax_percent: float
    tax_amount: float
    discount_percent: float
    discount_amount: float
    total: float
    status: str
    notes: Optional[str] = None
    pdf_url: Optional[str] = None
    payment_mode: str
    items: list[BillItemResponse] = []
    patient: Optional[PatientResponse] = None
    doctor: Optional[DoctorResponse] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ═══════════════════════════════════════════════════════════════
# Dashboard Schemas
# ═══════════════════════════════════════════════════════════════

class DashboardStats(BaseModel):
    total_revenue: float
    total_patients: int
    total_bills: int
    total_doctors: int
    today_revenue: float
    today_bills: int
    month_revenue: float
    month_bills: int


class RevenueChartData(BaseModel):
    label: str
    revenue: float
    count: int


class RecentTransaction(BaseModel):
    id: UUID
    bill_number: str
    patient_name: str
    total: float
    status: str
    payment_mode: str
    created_at: datetime


# ═══════════════════════════════════════════════════════════════
# Pagination
# ═══════════════════════════════════════════════════════════════

class PaginatedResponse(BaseModel):
    """Generic paginated response wrapper."""
    items: list
    total: int
    page: int
    page_size: int
    total_pages: int


# ═══════════════════════════════════════════════════════════════
# Super Admin Schemas
# ═══════════════════════════════════════════════════════════════

class PlatformStatsResponse(BaseModel):
    """Platform-wide analytics for superadmin dashboard."""
    total_tenants: int
    active_tenants: int
    total_users: int
    total_patients: int
    total_doctors: int
    total_bills: int
    total_revenue: float


class TenantDetailResponse(BaseModel):
    """Extended tenant info for superadmin management."""
    id: UUID
    name: str
    slug: str
    email: str
    phone: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    subscription_plan: str
    is_active: bool
    is_approved: bool
    biller_header: Optional[str] = None
    created_at: datetime
    user_count: int = 0
    patient_count: int = 0
    doctor_count: int = 0
    bill_count: int = 0
    total_revenue: float = 0.0


class TenantAdminUpdateRequest(BaseModel):
    """Superadmin updating a tenant's details."""
    is_active: Optional[bool] = None
    is_approved: Optional[bool] = None
    subscription_plan: Optional[str] = Field(None, pattern="^(free|basic|premium|enterprise)$")


# Resolve forward references
TokenResponse.model_rebuild()
