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
            if "localhost" not in v:
                params = []
                if "ssl" not in v.lower():
                    params.append("ssl=require")
                if "prepared_statement_cache_size" not in v:
                    params.append("prepared_statement_cache_size=0")
                if "statement_cache_size" not in v:
                    params.append("statement_cache_size=0")
                
                if params:
                    separator = "&" if "?" in v else "?"
                    v += f"{separator}{'&'.join(params)}"
        return v

    # ── JWT ───────────────────────────────────────────────────
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── CORS ──────────────────────────────────────────────────
    CORS_ORIGINS: str | List[str] = [
        "http://localhost:5173", 
        "http://localhost:3000",
        "https://hospital-billing-system-rho.vercel.app",
        "https://hospital-billing-system-lovat.vercel.app",
        "https://hospital-billing-system-git-main-traamakrishna3012.vercel.app"
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | List[str]) -> List[str]:
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return [origin.strip() for origin in v.split(",")]
        return v

    # ── Server ────────────────────────────────────────────────
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    APP_ENV: str = "development"
    APP_DEBUG: bool = True

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

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

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
