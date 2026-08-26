from __future__ import annotations

import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import ForeignKey as FK
from sqlalchemy import Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from packages.db.base import Base
from packages.db.enums import IdentifierType, ProductStatus
from packages.db.mixins import TimestampMixin, UpdatedAtMixin, UUIDPk

EMBEDDING_DIM = 1536


class Product(Base, UUIDPk, TimestampMixin, UpdatedAtMixin):
    """The canonical, market-agnostic entity. Created/merged into by entity
    resolution — see docs/DATA_MODEL.md and packages/entities."""

    __tablename__ = "product"

    canonical_title: Mapped[str] = mapped_column(Text)
    category: Mapped[str | None] = mapped_column(String(255), default=None)
    brand_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), FK("brand.id"), default=None
    )
    manufacturer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), FK("manufacturer.id"), default=None
    )
    primary_identifier_type: Mapped[IdentifierType] = mapped_column(default=IdentifierType.NONE)
    primary_identifier: Mapped[str | None] = mapped_column(String(64), default=None)
    status: Mapped[ProductStatus] = mapped_column(default=ProductStatus.ACTIVE)
    merged_into_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), FK("product.id"), default=None
    )


class ProductVariant(Base, UUIDPk, TimestampMixin, UpdatedAtMixin):
    """A specific sellable SKU as observed on one market's listing, before or
    after being linked to a canonical Product. product_id is NULL until
    entity resolution links it — see docs/DATA_MODEL.md."""

    __tablename__ = "product_variant"

    product_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), FK("product.id"), nullable=True, default=None, index=True
    )
    market_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), FK("market.id"))
    title_raw: Mapped[str] = mapped_column(Text)
    title_language: Mapped[str] = mapped_column(String(8))
    brand_raw: Mapped[str | None] = mapped_column(String(255), default=None)
    identifier_type: Mapped[IdentifierType] = mapped_column(default=IdentifierType.NONE)
    identifier_value: Mapped[str | None] = mapped_column(String(64), default=None, index=True)
    model_number: Mapped[str | None] = mapped_column(String(128), default=None)
    dimensions_mm: Mapped[dict | None] = mapped_column(JSONB, default=None)
    weight_g: Mapped[int | None] = mapped_column(Integer, default=None)
    capacity: Mapped[str | None] = mapped_column(String(64), default=None)
    material: Mapped[str | None] = mapped_column(String(128), default=None)
    color: Mapped[str | None] = mapped_column(String(64), default=None)
    pack_quantity: Mapped[int | None] = mapped_column(Integer, default=None)
    attributes_extra: Mapped[dict] = mapped_column(JSONB, default=dict)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIM), default=None)
