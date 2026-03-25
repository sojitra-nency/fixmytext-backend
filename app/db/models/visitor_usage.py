"""VisitorUsage ORM model — server-side trial tracking for unauthenticated users."""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, text
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.core.config import settings


class VisitorUsage(Base):
    __tablename__ = "visitor_usage"
    __table_args__ = {"schema": settings.DB_SCHEMA_AUTH}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()")
    )
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    # New INET column added in migration 0010 (replaces ip_address VARCHAR)
    ip_address_inet: Mapped[Optional[str]] = mapped_column(INET, nullable=True)
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True), nullable=True, server_default=text("now()"))
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=text("now()"))

    # DEPRECATED columns — kept alive during dual-write window (removed in migration 0015)
    ip_address: Mapped[str] = mapped_column(String(45), nullable=False, index=True)
    tool_uses_today: Mapped[dict] = mapped_column(JSONB, default=dict, server_default=text("'{}'::jsonb"))
    reset_date: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
