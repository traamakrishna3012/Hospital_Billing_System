"""
Model for tracking invalidated JWT tokens (logout strategy).
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import String, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class TokenBlocklist(Base):
    __tablename__ = "token_blocklist"

    jti: Mapped[str] = mapped_column(String(36), primary_key=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    def __repr__(self) -> str:
        return f"<TokenBlocklist {self.jti}>"
