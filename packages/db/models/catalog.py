from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ARRAY, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from packages.db.base import Base
from packages.db.enums import MarketplaceType
from packages.db.mixins import TimestampMixin, UUIDPk


class Brand(Base, UUIDPk, TimestampMixin):
    __tablename__ = "brand"

    name: Mapped[str] = mapped_column(String(255))
    name_normalized: Mapped[str] = mapped_column(String(255), index=True)
    aliases: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    country: Mapped[str | None] = mapped_column(String(2), default=None)


class Manufacturer(Base, UUIDPk, TimestampMixin):
    __tablename__ = "manufacturer"

    name: Mapped[str] = mapped_column(String(255))
    name_normalized: Mapped[str] = mapped_column(String(255), index=True)
    country: Mapped[str | None] = mapped_column(String(2), default=None)


class Market(Base, UUIDPk):
    __tablename__ = "market"

    code: Mapped[str] = mapped_column(String(8), unique=True)  # "JP", "KR"
    name: Mapped[str] = mapped_column(String(255))
    currency_code: Mapped[str] = mapped_column(String(3))  # "JPY", "KRW"


class Marketplace(Base, UUIDPk, TimestampMixin):
    __tablename__ = "marketplace"

    market_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("market.id"))
    name: Mapped[str] = mapped_column(String(255))
    marketplace_type: Mapped[MarketplaceType]
    base_url: Mapped[str | None] = mapped_column(Text, default=None)


class Seller(Base, UUIDPk):
    __tablename__ = "seller"

    marketplace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("marketplace.id")
    )
    external_seller_id: Mapped[str | None] = mapped_column(String(255), default=None)
    name: Mapped[str] = mapped_column(String(255))
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
