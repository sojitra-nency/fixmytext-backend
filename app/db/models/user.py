"""User ORM model — lives in the 'auth' schema."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, ForeignKey, String, text
from sqlalchemy.dialects.postgresql import TIMESTAMP, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.config import settings
from app.db.session import Base

if TYPE_CHECKING:
    from app.db.models.billing_credit import BillingUserCredit
    from app.db.models.billing_pass import BillingUserPass
    from app.db.models.billing_subscription import PaymentEvent, Subscription
    from app.db.models.gamification import UserGamification
    from app.db.models.operation_history import OperationHistory
    from app.db.models.preferences import UserPreferences
    from app.db.models.template import UserTemplate
    from app.db.models.user_pipeline import UserPipeline
    from app.db.models.user_ui_settings import UserUiSettings


class User(Base):
    __tablename__ = "users"
    __table_args__ = {"schema": settings.DB_SCHEMA_AUTH}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()")
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=text("now()"))
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()"), onupdate=datetime.now
    )
    last_login_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)

    # ── Referral ───────────────────────────────────────────────────────────────
    referral_code: Mapped[str | None] = mapped_column(String(20), unique=True, nullable=True)
    referred_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey(f"{settings.DB_SCHEMA_AUTH}.users.id", ondelete="SET NULL"), nullable=True
    )
    region: Mapped[str | None] = mapped_column(String(5), nullable=True)

    # ── Relationships ──────────────────────────────────────────────────────────
    preferences: Mapped[Optional["UserPreferences"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    ui_settings: Mapped[Optional["UserUiSettings"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    gamification: Mapped[Optional["UserGamification"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    templates: Mapped[list["UserTemplate"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    operation_history: Mapped[list["OperationHistory"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    pipelines: Mapped[list["UserPipeline"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    # Billing-schema entities
    subscriptions: Mapped[list["Subscription"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    payment_events: Mapped[list["PaymentEvent"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    billing_passes: Mapped[list["BillingUserPass"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    billing_credits: Mapped[list["BillingUserCredit"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
