"""Billing user_credits ORM model."""

import uuid
from datetime import datetime
from typing import Optional, TYPE_CHECKING

from sqlalchemy import String, SmallInteger, text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.core.config import settings

if TYPE_CHECKING:
    from app.db.models.user import User
    from app.db.models.billing_catalog import CreditPackCatalog


class BillingUserCredit(Base):
    __tablename__ = "user_credits"
    __table_args__ = {"schema": settings.DB_SCHEMA_BILLING}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{settings.DB_SCHEMA_AUTH}.users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    pack_id: Mapped[Optional[str]] = mapped_column(
        String(50),
        ForeignKey(f"{settings.DB_SCHEMA_BILLING}.credit_pack_catalog.id"),
        nullable=True,
    )
    credits_total: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    credits_remaining: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    source: Mapped[str] = mapped_column(String(30), nullable=False)
    razorpay_payment_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=text("now()"))

    user: Mapped["User"] = relationship(back_populates="billing_credits")
    pack_catalog: Mapped[Optional["CreditPackCatalog"]] = relationship(back_populates="user_credits")
