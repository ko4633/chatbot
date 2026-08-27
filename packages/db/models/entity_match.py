from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from packages.db.base import Base
from packages.db.enums import MatchStage, MatchType
from packages.db.mixins import AIProvenanceMixin, ProvenanceMixin, TimestampMixin, UUIDPk


class EntityMatch(Base, UUIDPk, TimestampMixin, ProvenanceMixin, AIProvenanceMixin):
    """Result of the entity resolution engine linking two ProductVariant rows.

    Never updated or deleted — a corrected match is a new row (docs/DATA_MODEL.md).
    """

    __tablename__ = "entity_match"

    left_variant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("product_variant.id"), index=True
    )
    right_variant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("product_variant.id"), index=True
    )
    match_type: Mapped[MatchType]
    match_stage: Mapped[MatchStage]
    match_confidence: Mapped[float] = mapped_column(Numeric(4, 3))
    evidence: Mapped[dict] = mapped_column(JSONB, default=dict)
    algorithm_version: Mapped[str] = mapped_column(String(32))
    resolved_product_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("product.id"), nullable=True, default=None
    )
    reviewed_by_human: Mapped[bool] = mapped_column(Boolean, default=False)
