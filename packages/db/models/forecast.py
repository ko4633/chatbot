from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from packages.db.base import Base
from packages.db.enums import ConfidenceTier, ForecastDirection
from packages.db.mixins import TimestampMixin, UUIDPk


class Forecast(Base, UUIDPk, TimestampMixin):
    """Qualitative direction only — `predicted_probability` is always NULL
    in Phase 2. See docs/ADR/0009-forecast-no-fabricated-probability.md."""

    __tablename__ = "forecast"

    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("product.id"), index=True)
    analysis_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("analysis_run.id")
    )
    forecast_created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    forecast_horizon_days: Mapped[int] = mapped_column(Integer)
    predicted_direction: Mapped[ForecastDirection]
    predicted_probability: Mapped[float | None] = mapped_column(Numeric(4, 3), default=None)
    confidence_tier: Mapped[ConfidenceTier]
    is_calibrated: Mapped[bool] = mapped_column(Boolean, default=False)
    model: Mapped[str] = mapped_column(String(64))
    evidence: Mapped[dict] = mapped_column(JSONB, default=dict)
    actual_outcome: Mapped[str | None] = mapped_column(String(32), default=None)
    evaluated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
