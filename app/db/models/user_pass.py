"""UserPass ORM model — tracks purchased/earned tool passes."""

import uuid
from datetime import datetime
from typing import Optional, TYPE_CHECKING

from sqlalchemy import String, Boolean, Integer, text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.core.config import settings

if TYPE_CHECKING:
    from app.db.models.user import User


class UserPass(Base):
    __tablename__ = "user_passes"
    __table_args__ = {"schema": settings.DB_SCHEMA_AUTH}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{settings.DB_SCHEMA_AUTH}.users.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    pass_id: Mapped[str] = mapped_column(String(50), nullable=False)  # catalog key e.g. 'day_triple'
    tool_ids: Mapped[list] = mapped_column(JSONB, default=list, server_default=text("'[]'::jsonb"))  # chosen tool IDs or ["*"]
    tools_count: Mapped[int] = mapped_column(Integer, nullable=False)  # 1,2,3,5,10,15 or -1 for all
    uses_per_day: Mapped[int] = mapped_column(Integer, nullable=False)  # daily use cap
    uses_today: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"))
    uses_reset_date: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    source: Mapped[str] = mapped_column(String(20), nullable=False)  # 'razorpay','earned','referral','spin','quest'
    purchased_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=text("now()"))
    expires_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))
    razorpay_payment_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    user: Mapped["User"] = relationship(back_populates="passes")
