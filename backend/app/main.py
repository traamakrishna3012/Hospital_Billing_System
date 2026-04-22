"""
Hospital Billing System — FastAPI Application Entry Point.

Production-ready multi-tenant billing system with:
- JWT authentication & role-based access control
- Multi-tenant data isolation via tenant_id
- Auto-generated API documentation (Swagger/OpenAPI)
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger

from app.core.config import get_settings
from app.core.database import init_db

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    logger.info("Starting Hospital Billing System...")

    # Create tables (use Alembic in production)
    await init_db()
    logger.info("Database initialized")

    # Ensure upload directories exist
    settings.upload_path  # triggers directory creation

    # Seed SuperAdmin if not exists
    try:
        from sqlalchemy import select, text
        from app.core.database import async_session_factory
        from app.models.user import User
        from app.core.security import hash_password
        
        async with async_session_factory() as db:
            # 1. Manual Migration - Users: tenant_id nullable, is_approved
            try:
                await db.execute(text("ALTER TABLE users ALTER COLUMN tenant_id DROP NOT NULL"))
                await db.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_approved BOOLEAN DEFAULT FALSE"))
                await db.commit()
                logger.info("Migration: users updated (tenant_id nullable, is_approved added)")
            except Exception as e:
                await db.rollback()
                logger.warning(f"Migration (users) skipped: {e}")

            # 2. Manual Migration - Tenants: is_approved, biller_header, modules
            try:
                await db.execute(text("ALTER TABLE tenants ADD COLUMN IF NOT EXISTS is_approved BOOLEAN DEFAULT FALSE"))
                await db.execute(text("ALTER TABLE tenants ADD COLUMN IF NOT EXISTS biller_header TEXT"))
                await db.execute(text('ALTER TABLE tenants ADD COLUMN IF NOT EXISTS modules JSON DEFAULT \'{"patients": true, "doctors": true, "tests": true, "billing": true, "reports": true, "staff": true}\'::json'))
                await db.commit()
                logger.info("Migration: tenants table updated with is_approved, biller_header, and modules")
            except Exception as e:
                await db.rollback()
                logger.warning(f"Migration (tenants table) skipped: {e}")

            # 3. Manual Migration - BillItems: code column
            try:
                await db.execute(text("ALTER TABLE bill_items ADD COLUMN IF NOT EXISTS code VARCHAR(50)"))
                await db.commit()
                logger.info("Migration: bill_items.code column added")
            except Exception as e:
                await db.rollback()
                logger.warning(f"Migration (bill_items.code) skipped: {e}")

            # 4. Manual Migration - Users: modules JSONB column
            try:
                await db.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS modules JSONB"))
                await db.commit()
                logger.info("Migration: users.modules column added")
            except Exception as e:
                await db.rollback()
                logger.warning(f"Migration (users.modules) skipped: {e}")

            # 5. Manual Migration - Tenants: logo_url to TEXT
            try:
                await db.execute(text("ALTER TABLE tenants ALTER COLUMN logo_url TYPE TEXT"))
                await db.commit()
                logger.info("Migration: tenants.logo_url changed to TEXT")
            except Exception as e:
                await db.rollback()
                logger.warning(f"Migration (tenants.logo_url) skipped: {e}")

            # 6. Manual Migration - Users: Auto-approve existing staff/doctors
            # Only users who are ALREADY part of a tenant and are not the primary admin
            # should be auto-approved if they are currently stuck.
            try:
                await db.execute(text("UPDATE users SET is_approved = true WHERE tenant_id IS NOT NULL AND role IN ('staff', 'doctor') AND is_approved = false"))
                await db.commit()
                logger.info("Migration: existing staff users auto-approved")
            except Exception as e:
                await db.rollback()
                logger.warning(f"Migration (staff auto-approval) skipped: {e}")

            # 3. Seed SuperAdmin
            result = await db.execute(
                select(User).where(User.email == "superadmin@hospitalbilling.com")
            )
            if not result.scalar_one_or_none():
                import os
                super_pw = os.getenv("SUPERADMIN_PASSWORD")
                if super_pw:
                    db.add(User(
                        email="superadmin@hospitalbilling.com",
                        password_hash=hash_password(super_pw),
                        full_name="System Super Admin",
                    role="superadmin",
                    tenant_id=None,
                    is_active=True,
                    is_approved=True
                ))
                await db.commit()
                logger.info("Successfully seeded superadmin in production DB.")
    except Exception as e:
        logger.error(f"Failed to seed or migrate during startup: {e}")

    yield

    logger.info("Shutting down...")


# ── FastAPI App ───────────────────────────────────────────────

app = FastAPI(
    title="Hospital Billing System API",
    description="Multi-tenant hospital/clinic billing system with patient, doctor, test, and billing management.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None if settings.is_production else "/redoc",
    openapi_url=None if settings.is_production else "/openapi.json",
)

# ── Middleware ────────────────────────────────────────────────

from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.core.limiter import limiter

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Add standard security headers to all responses."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    response.headers["Server"] = "Hidden" # Obscure server details
    return response

# ── Global Exception Handlers ────────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch unhandled exceptions and return structured error response."""
    logger.error(f"Unhandled error: {exc}", exc_info=True)
    
    if settings.is_production:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": "An internal server error occurred",
                "type": "InternalServerError",
            },
        )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": f"An internal server error occurred: {str(exc)}",
            "type": str(type(exc).__name__),
        },
    )


@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": "Resource not found"},
    )


# ── Static Files (uploads) ───────────────────────────────────

import os
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")


# ── Register API Routers ─────────────────────────────────────

from app.api.v1.auth import router as auth_router
from app.api.v1.patients import router as patients_router
from app.api.v1.doctors import router as doctors_router
from app.api.v1.tests import router as tests_router
from app.api.v1.bills import router as bills_router
from app.api.v1.clinic import router as clinic_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.users import router as users_router
from app.api.v1.reports import router as reports_router
from app.api.v1.superadmin import router as superadmin_router

API_PREFIX = "/api/v1"

app.include_router(auth_router, prefix=API_PREFIX)
app.include_router(patients_router, prefix=API_PREFIX)
app.include_router(doctors_router, prefix=API_PREFIX)
app.include_router(tests_router, prefix=API_PREFIX)
app.include_router(bills_router, prefix=API_PREFIX)
app.include_router(clinic_router, prefix=API_PREFIX)
app.include_router(dashboard_router, prefix=API_PREFIX)
app.include_router(users_router, prefix=API_PREFIX)
app.include_router(reports_router, prefix=API_PREFIX)
app.include_router(superadmin_router, prefix=API_PREFIX)


# ── Health Check ──────────────────────────────────────────────

@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "healthy", "version": "1.0.0"}


@app.get("/", tags=["Health"])
async def root():
    return {
        "message": "Hospital Billing System API",
        "docs": "/docs",
        "version": "1.0.0",
    }
