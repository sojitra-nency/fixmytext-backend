"""UserGamification ORM model."""

from datetime import datetime
from typing import Optional, TYPE_CHECKING

from sqlalchemy import String, Boolean, DateTime, Integer, Text, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

if TYPE_CHECKING:
    from app.db.models.user import User


class UserGamification(Base):
    __tablename__ = "user_gamification"

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    xp: Mapped[int] = mapped_column(Integer, default=0)
    streak_current: Mapped[int] = mapped_column(Integer, default=0)
    streak_last_date: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    total_ops: Mapped[int] = mapped_column(Integer, default=0)
    total_chars: Mapped[int] = mapped_column(Integer, default=0)
    tools_used: Mapped[str] = mapped_column(Text, default="{}")
    discovered_tools: Mapped[str] = mapped_column(Text, default="[]")
    achievements: Mapped[str] = mapped_column(Text, default="[]")
    favorites: Mapped[str] = mapped_column(Text, default="[]")
    saved_pipelines: Mapped[str] = mapped_column(Text, default="[]")
    completed_quests: Mapped[str] = mapped_column(Text, default="[]")
    daily_quest_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    daily_quest_date: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    daily_quest_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    user: Mapped["User"] = relationship(back_populates="gamification")
