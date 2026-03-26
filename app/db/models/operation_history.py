"""OperationHistory ORM model — lives in the 'activity' schema."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import String, Text, Integer, Boolean, ForeignKey
from sqlalchemy import text as sa_text
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.core.config import settings

if TYPE_CHECKING:
    from app.db.models.user import User


class OperationHistory(Base):
    __tablename__ = "operation_history"
    __table_args__ = {"schema": settings.DB_SCHEMA_ACTIVITY}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=sa_text("gen_random_uuid()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{settings.DB_SCHEMA_AUTH}.users.id", ondelete="CASCADE"),
        index=True,
    )

    # Tool identification
    tool_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    tool_label: Mapped[str] = mapped_column(String(200), nullable=False)
    tool_type: Mapped[str] = mapped_column(String(20), nullable=False)  # api, ai, local, select, action, drawer

    # Text snapshots (truncated to 500 chars to avoid bloating)
    input_preview: Mapped[str] = mapped_column(Text, nullable=False)
    output_preview: Mapped[str] = mapped_column(Text, nullable=False)
    input_length: Mapped[int] = mapped_column(Integer, nullable=False)
    output_length: Mapped[int] = mapped_column(Integer, nullable=False)

    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default=sa_text("'success'"))
    # Soft delete: set is_deleted=True instead of hard deleting (migration 0012)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=sa_text("false"))

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=sa_text("now()"), index=True
    )

    user: Mapped["User"] = relationship(back_populates="operation_history")
