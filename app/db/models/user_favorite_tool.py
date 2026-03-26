"""UserFavoriteTool ORM model — user's favorited tools with sort order."""

import uuid
from datetime import datetime

from sqlalchemy import SmallInteger, String, text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.core.config import settings


class UserFavoriteTool(Base):
    __tablename__ = "user_favorite_tools"
    __table_args__ = {"schema": settings.DB_SCHEMA_ACTIVITY}

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{settings.DB_SCHEMA_AUTH}.users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    tool_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    sort_order: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0, server_default=text("0"))
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=text("now()"))
