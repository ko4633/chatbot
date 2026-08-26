from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from packages.db.base import Base
from packages.db.enums import AIRunPurpose, AIRunStatus, AnalysisRunStatus, AnalysisRunType
from packages.db.mixins import TimestampMixin, UUIDPk


class AnalysisRun(Base, UUIDPk, TimestampMixin):
    """One pipeline execution. See docs/DATA_MODEL.md and
    docs/MASTER_SPEC.md §36 (observability ids)."""

    __tablename__ = "analysis_run"

    run_type: Mapped[AnalysisRunType]
    status: Mapped[AnalysisRunStatus] = mapped_column(default=AnalysisRunStatus.RUNNING)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    stats: Mapped[dict] = mapped_column(JSONB, default=dict)
    triggered_by: Mapped[str] = mapped_column(String(64))
    algorithm_version: Mapped[str] = mapped_column(String(32))
    error_detail: Mapped[str | None] = mapped_column(Text, default=None)


class AIRun(Base, UUIDPk, TimestampMixin):
    """Every AI provider call produces exactly one row here, including calls
    made while AI is disabled (status=DISABLED). See docs/AI_POLICY.md §7."""

    __tablename__ = "ai_run"

    analysis_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("analysis_run.id"), nullable=True, default=None
    )
    provider: Mapped[str] = mapped_column(String(64))
    model: Mapped[str] = mapped_column(String(128))
    purpose: Mapped[AIRunPurpose]
    input_tokens: Mapped[int | None] = mapped_column(Integer, default=None)
    output_tokens: Mapped[int | None] = mapped_column(Integer, default=None)
    cached_tokens: Mapped[int | None] = mapped_column(Integer, default=None)
    estimated_cost_usd: Mapped[float | None] = mapped_column(Numeric(10, 6), default=None)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    latency_ms: Mapped[int | None] = mapped_column(Integer, default=None)
    status: Mapped[AIRunStatus]
    prompt_version: Mapped[str] = mapped_column(String(32))
    error_detail: Mapped[str | None] = mapped_column(Text, default=None)
