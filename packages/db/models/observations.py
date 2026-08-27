"""Append-only Observation tables. ProvenanceMixin ONLY — no AI provenance
fields exist on these tables by construction. See docs/DATA_MODEL.md §3 and
docs/AI_POLICY.md §4."""

from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from packages.db.base import Base
from packages.db.enums import DemandMetricType
from packages.db.mixins import ProvenanceMixin, TimestampMixin, UUIDPk


class PriceObservation(Base, UUIDPk, TimestampMixin, ProvenanceMixin):
    __tablename__ = "price_observation"
    __table_args__ = (UniqueConstraint("offer_id", "source_snapshot_id"),)

    offer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("offer.id"), index=True
    )
    source_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("source.id"))
    source_snapshot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("source_snapshot.id")
    )
    price_amount: Mapped[int] = mapped_column(Integer)
    currency_code: Mapped[str] = mapped_column(String(3))


class InventoryObservation(Base, UUIDPk, TimestampMixin, ProvenanceMixin):
    __tablename__ = "inventory_observation"
    __table_args__ = (UniqueConstraint("offer_id", "source_snapshot_id"),)

    offer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("offer.id"), index=True
    )
    source_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("source.id"))
    source_snapshot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("source_snapshot.id")
    )
    in_stock: Mapped[bool] = mapped_column(Boolean)
    stock_quantity: Mapped[int | None] = mapped_column(Integer, default=None)


class ReviewObservation(Base, UUIDPk, TimestampMixin, ProvenanceMixin):
    __tablename__ = "review_observation"
    __table_args__ = (UniqueConstraint("product_variant_id", "source_snapshot_id"),)

    product_variant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("product_variant.id"), index=True
    )
    source_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("source.id"))
    source_snapshot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("source_snapshot.id")
    )
    review_count: Mapped[int] = mapped_column(Integer)
    average_rating: Mapped[float | None] = mapped_column(Numeric(3, 2), default=None)


class DemandObservation(Base, UUIDPk, TimestampMixin, ProvenanceMixin):
    __tablename__ = "demand_observation"
    __table_args__ = (UniqueConstraint("product_variant_id", "metric_type", "source_snapshot_id"),)

    product_variant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("product_variant.id"), index=True
    )
    source_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("source.id"))
    source_snapshot_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("source_snapshot.id")
    )
    metric_type: Mapped[DemandMetricType]
    metric_value: Mapped[float] = mapped_column(Numeric(12, 4))
    unit: Mapped[str] = mapped_column(String(32))
