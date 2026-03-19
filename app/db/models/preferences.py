"""UserPreferences ORM model — lives in the 'auth' schema."""

from datetime import datetime
from typing import Optional, TYPE_CHECKING
import uuid

from sqlalchemy import String, ForeignKey, text
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.core.config import settings

if TYPE_CHECKING:
    from app.db.models.user import User


class UserPreferences(Base):
    __tablename__ = "user_preferences"
    __table_args__ = {"schema": settings.DB_SCHEMA_AUTH}

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{settings.DB_SCHEMA_AUTH}.users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    theme: Mapped[str] = mapped_column(String(10), default="dark", server_default=text("'dark'"))
    persona: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    theme_skin: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=text("now()"), onupdate=datetime.now
    )

    user: Mapped["User"] = relationship(back_populates="preferences")
