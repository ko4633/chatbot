from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from packages.core.time_utils import utcnow
from packages.db.base import Base
from packages.db.enums import (
    DataMode,
    DataQualityStatus,
    ExtractionMethod,
    ReliabilityLevel,
    SnapshotStatus,
    SourceType,
    TrustTier,
)
from packages.db.mixins import TimestampMixin, UUIDPk


class Source(Base, UUIDPk, TimestampMixin):
    """Registry of everywhere data comes from. See docs/DATA_MODEL.md."""

    __tablename__ = "source"

    name: Mapped[str] = mapped_column(String(255))
    source_type: Mapped[SourceType]
    trust_tier: Mapped[TrustTier]
    factual_reliability: Mapped[ReliabilityLevel]
    signal_value: Mapped[ReliabilityLevel]
    country: Mapped[str | None] = mapped_column(String(2), default=None)
    base_url: Mapped[str | None] = mapped_column(Text, default=None)
    is_mock: Mapped[bool] = mapped_column(Boolean)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    data_mode: Mapped[DataMode] = mapped_column(default=DataMode.MOCK)
    data_quality_status: Mapped[DataQualityStatus] = mapped_column(default=DataQualityStatus.HEALTHY)
    last_quality_check_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)


class SourceSnapshot(Base, UUIDPk):
    """One fetch attempt. Append-only. See docs/DATA_MODEL.md."""

    __tablename__ = "source_snapshot"
    __table_args__ = (UniqueConstraint("source_id", "source_url", "retrieved_at"),)

    source_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("source.id"))
    source_url: Mapped[str] = mapped_column(Text)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    raw_object_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("raw_object.id"), nullable=True
    )
    parser_name: Mapped[str] = mapped_column(default="")
    parser_version: Mapped[str] = mapped_column(default="")
    extraction_method: Mapped[ExtractionMethod]
    status: Mapped[SnapshotStatus]
    error_detail: Mapped[str | None] = mapped_column(Text, default=None)
