"""Billing user_passes and user_pass_tools ORM models."""

import uuid
from datetime import date, datetime
from typing import Optional, TYPE_CHECKING

from sqlalchemy import String, Boolean, SmallInteger, Date, text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.core.config import settings

if TYPE_CHECKING:
    from app.db.models.user import User
    from app.db.models.billing_catalog import PassCatalog


class BillingUserPass(Base):
    __tablename__ = "user_passes"
    __table_args__ = {"schema": settings.DB_SCHEMA_BILLING}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{settings.DB_SCHEMA_AUTH}.users.id", ondelete="CASCADE"),
        nullable=False,
    )
    pass_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey(f"{settings.DB_SCHEMA_BILLING}.pass_catalog.id"),
        nullable=False,
    )
    # Denormalized at grant time so catalog changes don't affect existing passes
    tools_count: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    uses_per_day: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    source: Mapped[str] = mapped_column(String(20), nullable=False)
    razorpay_payment_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    purchased_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=text("now()"))
    expires_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
    uses_today: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0, server_default=text("0"))
    uses_reset_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    user: Mapped["User"] = relationship(back_populates="billing_passes")
    pass_catalog: Mapped["PassCatalog"] = relationship(back_populates="user_passes")
    tools: Mapped[list["UserPassTool"]] = relationship(back_populates="pass_instance", cascade="all, delete-orphan")


class UserPassTool(Base):
    __tablename__ = "user_pass_tools"
    __table_args__ = {"schema": settings.DB_SCHEMA_BILLING}

    pass_instance_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{settings.DB_SCHEMA_BILLING}.user_passes.id", ondelete="CASCADE"),
        primary_key=True,
    )
    tool_id: Mapped[str] = mapped_column(String(100), primary_key=True)

    pass_instance: Mapped["BillingUserPass"] = relationship(back_populates="tools")
