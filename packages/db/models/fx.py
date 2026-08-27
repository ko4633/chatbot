from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from packages.db.base import Base
from packages.db.mixins import ProvenanceMixin, TimestampMixin, UUIDPk


class FXObservation(Base, UUIDPk, TimestampMixin, ProvenanceMixin):
    """Append-only FX rate time series. See docs/DATA_MODEL.md
    `fx_observation` and docs/ADR/0006-fx-provider-architecture.md."""

    __tablename__ = "fx_observation"
    __table_args__ = (UniqueConstraint("base_currency", "quote_currency", "source_id", "observed_at"),)

    base_currency: Mapped[str] = mapped_column(String(3), index=True)
    quote_currency: Mapped[str] = mapped_column(String(3), index=True)
    rate: Mapped[float] = mapped_column(Numeric(18, 6))
    provider_name: Mapped[str] = mapped_column(String(32))
    is_live: Mapped[bool]

    # ProvenanceMixin.source_id is nullable by default (Insight/Opportunity
    # use-case); FX always has exactly one contributing source, so require it.
    source_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("source.id"))
