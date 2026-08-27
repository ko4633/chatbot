from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from packages.db.base import Base
from packages.db.enums import OpportunityStatus, OpportunityType, RegulationStatus
from packages.db.mixins import (
    AIProvenanceMixin,
    ProvenanceMixin,
    TimestampMixin,
    UpdatedAtMixin,
    UUIDPk,
)


class Opportunity(Base, UUIDPk, TimestampMixin, UpdatedAtMixin, ProvenanceMixin, AIProvenanceMixin):
    """An actionable candidate. opportunity_score and confidence_score are
    independent axes — see docs/AI_POLICY.md and ADR-0003. Never let AI write
    to opportunity_score/confidence_score/sub_scores; only narrative fields
    (carried in a linked Insight) may be AI-assisted."""

    __tablename__ = "opportunity"

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("product.id"), index=True
    )
    opportunity_type: Mapped[OpportunityType]
    opportunity_score: Mapped[float] = mapped_column(Numeric(5, 2))
    confidence_score: Mapped[float] = mapped_column(Numeric(5, 2))
    sub_scores: Mapped[dict] = mapped_column(JSONB)
    weights_version: Mapped[str] = mapped_column(String(32))
    economics: Mapped[dict] = mapped_column(JSONB)
    regulation_status: Mapped[RegulationStatus] = mapped_column(default=RegulationStatus.UNKNOWN)
    regulation_basis: Mapped[str | None] = mapped_column(Text, default=None)
    status: Mapped[OpportunityStatus] = mapped_column(default=OpportunityStatus.NEW)
    analysis_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("analysis_run.id")
    )
