from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from packages.db.base import Base
from packages.db.enums import OfferStatus
from packages.db.mixins import TimestampMixin, UpdatedAtMixin, UUIDPk


class Offer(Base, UUIDPk, TimestampMixin, UpdatedAtMixin):
    """A specific seller's listing of a ProductVariant on a Marketplace.
    See docs/DATA_MODEL.md."""

    __tablename__ = "offer"
    __table_args__ = (UniqueConstraint("marketplace_id", "listing_url"),)

    product_variant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("product_variant.id"), index=True
    )
    marketplace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("marketplace.id")
    )
    seller_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("seller.id"), nullable=True, default=None
    )
    listing_url: Mapped[str] = mapped_column(Text)
    currency_code: Mapped[str] = mapped_column(String(3))
    status: Mapped[OfferStatus] = mapped_column(default=OfferStatus.ACTIVE)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
