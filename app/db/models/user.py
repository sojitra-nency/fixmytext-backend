"""User ORM model."""

import uuid
from datetime import datetime
from typing import Optional, TYPE_CHECKING

from sqlalchemy import String, Boolean, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

if TYPE_CHECKING:
    from app.db.models.preferences import UserPreferences
    from app.db.models.gamification import UserGamification
    from app.db.models.template import UserTemplate


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    preferences: Mapped[Optional["UserPreferences"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    gamification: Mapped[Optional["UserGamification"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    templates: Mapped[list["UserTemplate"]] = relationship(back_populates="user", cascade="all, delete-orphan")
