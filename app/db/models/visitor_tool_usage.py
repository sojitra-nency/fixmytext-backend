"""VisitorToolUsage ORM model — per-visitor per-tool per-day counter for anonymous users."""

import uuid
from datetime import date

from sqlalchemy import String, SmallInteger, Date, text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.core.config import settings


class VisitorToolUsage(Base):
    __tablename__ = "visitor_tool_usage"
    __table_args__ = {"schema": settings.DB_SCHEMA_AUTH}

    visitor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{settings.DB_SCHEMA_AUTH}.visitor_usage.id", ondelete="CASCADE"),
        primary_key=True,
    )
    tool_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    usage_date: Mapped[date] = mapped_column(
        Date, primary_key=True, server_default=text("CURRENT_DATE")
    )
    use_count: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=1, server_default=text("1")
    )
