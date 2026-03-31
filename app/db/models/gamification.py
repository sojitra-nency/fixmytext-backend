"""UserGamification ORM model — lives in the 'activity' schema."""

from datetime import date, datetime
from typing import Optional, TYPE_CHECKING
import uuid

from sqlalchemy import String, Boolean, Integer, BigInteger, Date, text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.core.config import settings

if TYPE_CHECKING:
    from app.db.models.user import User


class UserGamification(Base):
    __tablename__ = "user_gamification"
    __table_args__ = {"schema": settings.DB_SCHEMA_ACTIVITY}

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{settings.DB_SCHEMA_AUTH}.users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    xp: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"))
    streak_current: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"))

    streak_last_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    daily_quest_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    total_ops: Mapped[int] = mapped_column(Integer, default=0, server_default=text("0"))
    # BIGINT upgrade from INTEGER (migration 0011) — can handle high-volume users
    total_chars: Mapped[int] = mapped_column(BigInteger, default=0, server_default=text("0"))

    # ── JSONB kept: bounded append-only sets, only need membership checks via GIN ──
    achievements: Mapped[list] = mapped_column(JSONB, default=list, server_default=text("'[]'::jsonb"))
    completed_quests: Mapped[list] = mapped_column(JSONB, default=list, server_default=text("'[]'::jsonb"))

    daily_quest_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    daily_quest_completed: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()"), onupdate=datetime.now
    )

    user: Mapped["User"] = relationship(back_populates="gamification")
