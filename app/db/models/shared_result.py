"""SharedResult ORM model — lives in the 'activity' schema."""

import uuid
from datetime import datetime
from typing import Optional, TYPE_CHECKING

from sqlalchemy import String, Text, ForeignKey
from sqlalchemy import text as sa_text
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.core.config import settings

if TYPE_CHECKING:
    from app.db.models.user import User


class SharedResult(Base):
    __tablename__ = "shared_results"
    __table_args__ = {"schema": settings.DB_SCHEMA_ACTIVITY}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=sa_text("gen_random_uuid()")
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{settings.DB_SCHEMA_AUTH}.users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Tool that produced this result
    tool_id: Mapped[str] = mapped_column(String(100), nullable=False)
    tool_label: Mapped[str] = mapped_column(String(200), nullable=False)

    # Output text only
    output_text: Mapped[str] = mapped_column(Text, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=sa_text("now()"), index=True
    )

    user: Mapped[Optional["User"]] = relationship()
