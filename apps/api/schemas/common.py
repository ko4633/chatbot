from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class SourceRef(ORMModel):
    id: uuid.UUID
    name: str
    source_type: str
    trust_tier: str
    factual_reliability: str
    signal_value: str
    is_mock: bool
    data_mode: str  # "MOCK" | "LIVE" | "MANUAL" — docs/ADR/0007-explicit-data-mode-field.md
    base_url: str | None = None


class PriceHistoryPoint(BaseModel):
    observed_at: datetime
    price_amount: int
    currency_code: str
    source_snapshot_id: uuid.UUID | None = None
