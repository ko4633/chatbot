from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from packages.db.base import Base
from packages.db.enums import EventEntityType, EventType
from packages.db.mixins import TimestampMixin, UUIDPk


class Event(Base, UUIDPk, TimestampMixin):
    """A detected change between two points in time. See docs/DATA_MODEL.md."""

    __tablename__ = "event"

    entity_type: Mapped[EventEntityType]
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    event_type: Mapped[EventType]
    previous_value: Mapped[dict] = mapped_column(JSONB)
    new_value: Mapped[dict] = mapped_column(JSONB)
    change_pct: Mapped[float | None] = mapped_column(Numeric(8, 4), default=None)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    evidence: Mapped[dict] = mapped_column(JSONB, default=dict)
    confidence: Mapped[float] = mapped_column(Numeric(4, 3))
    analysis_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("analysis_run.id")
    )
