"""
Hospital Billing System — FastAPI Application Entry Point.

Production-ready multi-tenant billing system with:
- JWT authentication & role-based access control
- Multi-tenant data isolation via tenant_id
- Auto-generated API documentation (Swagger/OpenAPI)
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.gzip import GZipMiddleware
import sys
from loguru import logger

from app.core.config import get_settings
from app.core.database import init_db

settings = get_settings()

# Configure loguru to use stdout (to avoid red bars in Railway/Render)
logger.remove()
logger.add(sys.stdout, format="{time} | {level} | {message}", level="INFO")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    logger.info("Starting Hospital Billing System...")

    # Create tables (use Alembic in production)
    # We now handle this in app/prestart.py for faster worker boot.
    # But we keep a simple init check here just in case.
    try:
        await init_db()
    except Exception as e:
        logger.error(f"Startup database check failed: {e}")

    # Log static directory for debugging
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    static_dir = os.path.join(base_dir, "static")
    logger.info(f"Static directory: {static_dir}")
    if os.path.exists(static_dir):
        logger.info(f"Static directory contents: {os.listdir(static_dir)}")
    else:
        logger.warning("Static directory does NOT exist!")

    # Background task: prune expired tokens from the blocklist every 6 hours

    import asyncio
    from datetime import datetime, timezone
    from sqlalchemy import delete as sql_delete
    from app.models.token_blocklist import TokenBlocklist
    from app.core.database import async_session_factory

    async def cleanup_expired_tokens():
        """Remove expired tokens from blocklist every 6 hours."""
        while True:
            await asyncio.sleep(6 * 3600)
            try:
                async with async_session_factory() as db:
                    result = await db.execute(
                        sql_delete(TokenBlocklist).where(
                            TokenBlocklist.expires_at < datetime.now(timezone.utc)
                        )
                    )
                    await db.commit()
                    logger.info(f"Token blocklist cleanup: {result.rowcount} expired entries removed")
            except Exception as e:
                logger.error(f"Token cleanup error: {e}")

    cleanup_task = asyncio.create_task(cleanup_expired_tokens())

    yield

    cleanup_task.cancel()
    logger.info("Shutting down...")


# ── FastAPI App ───────────────────────────────────────────────

from fastapi.responses import ORJSONResponse

app = FastAPI(
    title="Hospital Billing API",
    description="Multi-tenant hospital/clinic billing system with patient, doctor, test, and billing management.",
    version="1.0.0",
    lifespan=lifespan,
    default_response_class=ORJSONResponse,
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
    openapi_url="/openapi.json" if not settings.is_production else None,
)
logger.info(f"Docs enabled: {not settings.is_production}")

# ── Middleware ────────────────────────────────────────────────

from starlette.middleware.base import BaseHTTPMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.core.limiter import limiter
import traceback

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# V-12: CORS — explicit allowlist only, no wildcards
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


# V-09: Security headers — class-based middleware
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com data:; "
            "img-src 'self' data: blob:; "
            "connect-src 'self' *; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self';"
        )


        response.headers["Server"] = "Hidden"
        return response


app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# ── Global Exception Handlers ────────────────────────────────

# V-10: Never leak stack traces to clients in production
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch unhandled exceptions and return structured error response."""
    logger.error(f"Unhandled exception: {traceback.format_exc()}")

    if settings.is_production:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "An unexpected error occurred. Please contact support."},
        )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": str(exc)},
    )


@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": "Resource not found"},
    )


# ── Static Files (uploads) ───────────────────────────────────

# os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
# app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")


# ── Health Check ──────────────────────────────────────────────
# Always keep this at the top to ensure monitoring works even if other parts fail
@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "healthy", "version": "1.0.1"}


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


# ── SPA Frontend Serving ─────────────────────────────────────
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Path to the static files directory (populated during Docker build)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(BASE_DIR, "static")

class SPAStaticFiles(StaticFiles):
    """Custom StaticFiles that serves index.html for 404s (SPA routing)."""
    async def get_response(self, path: str, scope):
        try:
            response = await super().get_response(path, scope)
            
            # ── Cache Headers for Performance ────────────────────────
            if path == "" or path == "index.html" or response.status_code == 404:
                # NEVER cache index.html (always check for new version)
                response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
                response.headers["Pragma"] = "no-cache"
                response.headers["Expires"] = "0"
            else:
                # LONG cache for assets (hashed by Vite, so safe to cache forever)
                # 31536000 seconds = 1 year
                response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
            
            return response
        except (HTTPException, Exception) as e:
            # If it's an API call or a file that SHOULD exist (has extension), don't fallback to index.html
            path_str = scope["path"]
            if path_str.startswith("/api") or "." in path_str.split("/")[-1]:
                raise e
            
            index_path = os.path.join(STATIC_DIR, "index.html")
            if os.path.exists(index_path):
                response = FileResponse(index_path)
                # NEVER cache index.html fallback
                response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
                return response
            raise e


# Mount the SPA handler at root
if os.path.exists(STATIC_DIR):
    app.mount("/", SPAStaticFiles(directory=STATIC_DIR, html=True), name="spa")
else:
    logger.warning(f"Static directory {STATIC_DIR} not found. Frontend serving disabled.")




