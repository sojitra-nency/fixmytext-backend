"""Billing catalog ORM models — pass_catalog, pass_catalog_prices, credit_pack_catalog, credit_pack_prices."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import String, Boolean, SmallInteger, Integer, text
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.core.config import settings

if TYPE_CHECKING:
    from app.db.models.billing_pass import BillingUserPass
    from app.db.models.billing_credit import BillingUserCredit


class PassCatalog(Base):
    __tablename__ = "pass_catalog"
    __table_args__ = {"schema": settings.DB_SCHEMA_BILLING}

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    subtitle: Mapped[str] = mapped_column(String(200), nullable=False)
    tools_count: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    uses_per_day: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    duration_days: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
    display_order: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0, server_default=text("0"))
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=text("now()"))

    prices: Mapped[list["PassCatalogPrice"]] = relationship(back_populates="pass_catalog", cascade="all, delete-orphan")
    user_passes: Mapped[list["BillingUserPass"]] = relationship(back_populates="pass_catalog")


class PassCatalogPrice(Base):
    __tablename__ = "pass_catalog_prices"
    __table_args__ = {"schema": settings.DB_SCHEMA_BILLING}

    pass_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    region: Mapped[str] = mapped_column(String(5), primary_key=True)
    amount_subunits: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), nullable=False)

    pass_catalog: Mapped["PassCatalog"] = relationship(back_populates="prices")


class CreditPackCatalog(Base):
    __tablename__ = "credit_pack_catalog"
    __table_args__ = {"schema": settings.DB_SCHEMA_BILLING}

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    credits: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
    display_order: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0, server_default=text("0"))
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=text("now()"))

    prices: Mapped[list["CreditPackPrice"]] = relationship(back_populates="pack_catalog", cascade="all, delete-orphan")
    user_credits: Mapped[list["BillingUserCredit"]] = relationship(back_populates="pack_catalog")


class CreditPackPrice(Base):
    __tablename__ = "credit_pack_prices"
    __table_args__ = {"schema": settings.DB_SCHEMA_BILLING}

    pack_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    region: Mapped[str] = mapped_column(String(5), primary_key=True)
    amount_subunits: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), nullable=False)

    pack_catalog: Mapped["CreditPackCatalog"] = relationship(back_populates="prices")
