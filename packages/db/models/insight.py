from __future__ import annotations

import uuid

from sqlalchemy import ARRAY, Boolean, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from packages.db.base import Base
from packages.db.enums import InsightKind
from packages.db.mixins import AIProvenanceMixin, ProvenanceMixin, TimestampMixin, UUIDPk


class Insight(Base, UUIDPk, TimestampMixin, ProvenanceMixin, AIProvenanceMixin):
    """A cross-cutting interpretation connecting multiple facts/events.
    See docs/DATA_MODEL.md and docs/ADR/0008-insight-kind-enum.md."""

    __tablename__ = "insight"

    product_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("product.id"), nullable=True, default=None, index=True
    )
    kind: Mapped[InsightKind] = mapped_column(index=True)
    title: Mapped[str] = mapped_column(Text)
    narrative: Mapped[str] = mapped_column(Text)
    supporting_facts: Mapped[list] = mapped_column(JSONB, default=list)
    is_ai_generated: Mapped[bool] = mapped_column(Boolean)
    ai_assisted_fields: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    confidence: Mapped[float] = mapped_column(Numeric(4, 3))
    analysis_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("analysis_run.id")
    )
