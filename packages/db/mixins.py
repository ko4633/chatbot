"""Reusable column mixins. See docs/DATA_MODEL.md §3.

ProvenanceMixin is applied to every Observation table AND to entity_match /
insight / opportunity. AIProvenanceMixin is applied ONLY to tables where AI
involvement is legitimately possible (entity_match, insight, opportunity,
product_variant for embeddings) — never to the four raw Observation tables.
This is a structural enforcement of "AI output never becomes a Fact/Observation"
(docs/AI_POLICY.md §4): there is no column to write AI provenance into on
those tables even if someone tried.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from packages.core.ids import new_id
from packages.core.time_utils import utcnow
from packages.db.enums import ExtractionMethod


class UUIDPk:
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_id)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class UpdatedAtMixin:
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class ProvenanceMixin:
    """Minimum provenance fields required on every external observation.

    source_id/source_snapshot_id default to nullable here because Insight/
    Opportunity rows aggregate many sources and record them in a JSONB
    evidence field instead of a single FK; the four Observation tables
    override both as NOT NULL since they always come from exactly one fetch.
    See docs/MASTER_SPEC.md §4.
    """

    source_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("source.id"), nullable=True, default=None
    )
    source_snapshot_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("source_snapshot.id"), nullable=True, default=None
    )
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    parser_name: Mapped[str] = mapped_column(default="")
    parser_version: Mapped[str] = mapped_column(default="")
    extraction_method: Mapped[ExtractionMethod]
    confidence: Mapped[float] = mapped_column(Numeric(4, 3))


class AIProvenanceMixin:
    """Extra provenance recorded only when an AI call contributed to the row.

    Nullable throughout — most rows will not have these set.
    """

    model_provider: Mapped[str | None] = mapped_column(default=None)
    model_name: Mapped[str | None] = mapped_column(default=None)
    prompt_version: Mapped[str | None] = mapped_column(default=None)
    ai_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_run.id"), nullable=True, default=None
    )
