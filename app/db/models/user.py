"""User ORM model — lives in the 'auth' schema."""

import uuid
from datetime import datetime
from typing import Optional, TYPE_CHECKING

from sqlalchemy import String, Boolean, Integer, text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.core.config import settings

if TYPE_CHECKING:
    from app.db.models.preferences import UserPreferences
    from app.db.models.gamification import UserGamification
    from app.db.models.template import UserTemplate
    from app.db.models.user_pass import UserPass
    from app.db.models.user_credit import UserCredit


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

    # ── Razorpay / Subscription ───────────────────────────────────────────────
    subscription_tier: Mapped[str] = mapped_column(String(20), default="free", server_default=text("'free'"))
    razorpay_subscription_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # ── Per-tool usage tracking ────────────────────────────────────────────────
    tool_uses_today: Mapped[dict] = mapped_column(JSONB, default=dict, server_default=text("'{}'::jsonb"))
    tool_uses_reset_date: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)

    # ── Retention / Engagement ─────────────────────────────────────────────────
    daily_login_date: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    last_spin_date: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    referral_code: Mapped[Optional[str]] = mapped_column(String(20), unique=True, nullable=True)
    referred_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey(f"{settings.DB_SCHEMA_AUTH}.users.id", ondelete="SET NULL"), nullable=True
    )
    region: Mapped[Optional[str]] = mapped_column(String(5), nullable=True)

    # ── Relationships (cross-schema) ───────────────────────────────────────────
    preferences: Mapped[Optional["UserPreferences"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    gamification: Mapped[Optional["UserGamification"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    templates: Mapped[list["UserTemplate"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    passes: Mapped[list["UserPass"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    credits: Mapped[list["UserCredit"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
