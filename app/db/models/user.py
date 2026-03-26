"""User ORM model — lives in the 'auth' schema."""

import uuid
from datetime import datetime
from typing import Optional, TYPE_CHECKING

from sqlalchemy import String, Boolean, text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.core.config import settings

if TYPE_CHECKING:
    from app.db.models.preferences import UserPreferences
    from app.db.models.user_ui_settings import UserUiSettings
    from app.db.models.gamification import UserGamification
    from app.db.models.template import UserTemplate
    from app.db.models.user_pass import UserPass
    from app.db.models.user_credit import UserCredit
    from app.db.models.operation_history import OperationHistory
    from app.db.models.billing_subscription import Subscription, PaymentEvent
    from app.db.models.billing_pass import BillingUserPass
    from app.db.models.billing_credit import BillingUserCredit
    from app.db.models.user_pipeline import UserPipeline


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
    last_login_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True), nullable=True)

    # ── Referral ───────────────────────────────────────────────────────────────
    referral_code: Mapped[Optional[str]] = mapped_column(String(20), unique=True, nullable=True)
    referred_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey(f"{settings.DB_SCHEMA_AUTH}.users.id", ondelete="SET NULL"), nullable=True
    )
    region: Mapped[Optional[str]] = mapped_column(String(5), nullable=True)

    # ── DEPRECATED columns — kept alive during dual-write window (removed in migration 0015) ──
    subscription_tier: Mapped[str] = mapped_column(String(20), default="free", server_default=text("'free'"))
    razorpay_subscription_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    tool_uses_today: Mapped[dict] = mapped_column(JSONB, default=dict, server_default=text("'{}'::jsonb"))
    tool_uses_reset_date: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    daily_login_date: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    last_spin_date: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)

    # ── Relationships ──────────────────────────────────────────────────────────
    preferences: Mapped[Optional["UserPreferences"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    ui_settings: Mapped[Optional["UserUiSettings"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    gamification: Mapped[Optional["UserGamification"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    templates: Mapped[list["UserTemplate"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    operation_history: Mapped[list["OperationHistory"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    pipelines: Mapped[list["UserPipeline"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    # Legacy auth-schema passes/credits (kept during dual-write window)
    passes: Mapped[list["UserPass"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    credits: Mapped[list["UserCredit"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    # New billing-schema entities
    subscriptions: Mapped[list["Subscription"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    payment_events: Mapped[list["PaymentEvent"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    billing_passes: Mapped[list["BillingUserPass"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    billing_credits: Mapped[list["BillingUserCredit"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
