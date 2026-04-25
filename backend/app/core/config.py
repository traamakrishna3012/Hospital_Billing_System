"""
Application configuration management.
Uses Pydantic Settings for type-safe environment variable parsing.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Database ──────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost:5432/hospital_billing"

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def parse_database_url(cls, v: str) -> str:
        if v:
            if v.startswith("postgresql://"):
                v = v.replace("postgresql://", "postgresql+asyncpg://", 1)
            # Don't force SSL for local connections (localhost or docker service name 'db')
            is_local = "localhost" in v or "127.0.0.1" in v or "@db:" in v
            if not is_local and "ssl" not in v.lower():
                separator = "&" if "?" in v else "?"
                v += f"{separator}ssl=require"
        return v

    # ── JWT ───────────────────────────────────────────────────
    JWT_SECRET_KEY: str = "placeholder-secret-key-that-is-at-least-64-characters-long-for-validation"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    @field_validator("JWT_SECRET_KEY", mode="after")
    @classmethod
    def validate_jwt_secret(cls, v: str, info) -> str:
        _WEAK_DEFAULTS = {
            "change-this-in-production",
            "secret",
            "supersecret",
            "your-secret-key",
            "jwt-secret",
            "changeme",
            "placeholder-secret-key-that-is-at-least-64-characters-long-for-validation"
        }
        # Access APP_ENV from the data if available
        is_prod = info.data.get("APP_ENV", "development") == "production"
        
        if is_prod and (len(v) < 32 or v.lower().strip() in _WEAK_DEFAULTS):
            raise ValueError(
                "CRITICAL: JWT_SECRET_KEY must be at least 32 characters and must not use default values in PRODUCTION."
            )
        return v

    # ── CORS ──────────────────────────────────────────────────
    CORS_ORIGINS: str | List[str] = ["http://localhost:8000", "http://127.0.0.1:8000", "http://localhost:5173"] 


    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | List[str]) -> List[str]:
        if not v:
            return ["http://localhost:8000"]
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return [origin.strip() for origin in v.split(",")]
        return v

    # ── Server ────────────────────────────────────────────────
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    APP_ENV: str = "production"
    APP_DEBUG: bool = False

    # ── File Uploads ──────────────────────────────────────────
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE_MB: int = 5

    # ── Email (SMTP) ──────────────────────────────────────────
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_NAME: str = "Hospital Billing System"
    SMTP_FROM_EMAIL: str = ""
    SMTP_TLS: bool = True

    # ── Defaults ──────────────────────────────────────────────
    DEFAULT_TAX_PERCENT: float = 18.0
    DEFAULT_CURRENCY: str = "INR"

    # ── SuperAdmin ────────────────────────────────────────────
    SUPERADMIN_EMAIL: str = "superadmin@hospitalbilling.com"
    SUPERADMIN_PASSWORD: str = "Admin@123"

    # ── VAPT / Hardening ──────────────────────────────────────
    COOKIE_SECURE: bool = True
    COOKIE_SAMESITE: str = "lax"
    AUTH_TOKEN_KEY: str = "access_token"
    REFRESH_TOKEN_KEY: str = "refresh_token"


    @property
    def is_production(self) -> bool:
        return self.APP_ENV != "development"

    @property
    def upload_path(self) -> Path:
        path = Path(self.UPLOAD_DIR)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def max_upload_bytes(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    @property
    def email_enabled(self) -> bool:
        return bool(self.SMTP_HOST and self.SMTP_USER and self.SMTP_PASSWORD)


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()
