"""UserDiscoveredTool ORM model — tracks when a user first used each tool."""

import uuid
from datetime import datetime

from sqlalchemy import String, text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.core.config import settings


class UserDiscoveredTool(Base):
    __tablename__ = "user_discovered_tools"
    __table_args__ = {"schema": settings.DB_SCHEMA_ACTIVITY}

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{settings.DB_SCHEMA_AUTH}.users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    tool_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    discovered_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=text("now()"))
