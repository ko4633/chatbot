from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel

from apps.api.schemas.common import PriceHistoryPoint, SourceRef


class OpportunityListItem(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    product_title: str
    opportunity_score: float
    confidence_score: float
    market_pair: str  # "JP -> KR"
    japan_purchase_price_jpy: int
    korea_sale_price_krw: int
    expected_margin_krw: float
    kr_seller_count: int
    status: str
    is_mock: bool
    data_mode: str  # "MOCK" | "LIVE" | "MANUAL" — docs/ADR/0007
    created_at: datetime


class OpportunityListResponse(BaseModel):
    items: list[OpportunityListItem]
    total: int
    data_mode: str  # "mock" | "live" | "mixed"


class OpportunityHistoryPoint(BaseModel):
    """One point in a product's opportunity time series — docs/MASTER_SPEC.md
    §6 "reconstruct state at a point in time". Backed directly by retained
    Opportunity rows (superseded ones are marked STALE, never deleted —
    see docs/EVALUATION.md §6), not a separate history table."""

    opportunity_id: uuid.UUID
    analysis_run_id: uuid.UUID
    status: str
    opportunity_score: float
    confidence_score: float
    contribution_margin_krw: float | None
    jpy_krw_fx: float | None
    japan_purchase_price_jpy: int | None
    korea_sale_price_krw: int | None
    created_at: datetime


class OpportunityHistoryResponse(BaseModel):
    product_id: uuid.UUID
    as_of: datetime | None  # echoes the ?as_of filter, null when none was given
    points: list[OpportunityHistoryPoint]
    current: OpportunityHistoryPoint | None  # the point that was "current" as_of that time


class EntityMatchEvidenceItem(BaseModel):
    id: uuid.UUID
    left_variant_id: uuid.UUID
    right_variant_id: uuid.UUID
    left_title: str
    right_title: str
    match_type: str
    match_stage: str
    match_confidence: float
    evidence: dict
    algorithm_version: str


class EventItem(BaseModel):
    id: uuid.UUID
    event_type: str
    previous_value: dict
    new_value: dict
    change_pct: float | None
    observed_at: datetime
    confidence: float


class InsightItem(BaseModel):
    id: uuid.UUID
    kind: str  # docs/ADR/0008 — filter on this, not title
    title: str
    narrative: str
    is_ai_generated: bool
    confidence: float


class UserDecisionItem(BaseModel):
    id: uuid.UUID
    decision: str
    reason: str | None
    note: str | None
    created_at: datetime


class ForecastItem(BaseModel):
    """docs/ADR/0009: direction/confidence_tier only — predicted_probability
    is always null and is_calibrated always false in Phase 2. The UI must
    show is_calibrated, not just the label, so it reads as a qualitative
    hint rather than a statistic."""

    id: uuid.UUID
    predicted_direction: str
    predicted_probability: float | None
    confidence_tier: str
    is_calibrated: bool
    forecast_horizon_days: int
    evidence: dict
    created_at: datetime


class UserDecisionCreate(BaseModel):
    decision: str
    reason: str | None = None
    note: str | None = None
    user_email: str


class OpportunityDetail(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    product_title: str
    opportunity_type: str
    opportunity_score: float
    confidence_score: float
    sub_scores: dict
    weights_version: str
    economics: dict
    regulation_status: str
    regulation_basis: str | None
    status: str
    created_at: datetime
    analysis_run_id: uuid.UUID

    japan_offers: list[dict]
    korea_offers: list[dict]
    price_history_jp: list[PriceHistoryPoint]
    price_history_kr: list[PriceHistoryPoint]
    entity_matches: list[EntityMatchEvidenceItem]
    events: list[EventItem]
    insights: list[InsightItem]
    sources: list[SourceRef]
    decisions: list[UserDecisionItem]
    is_mock: bool
    data_mode: str  # "MOCK" | "LIVE" | "MANUAL" — docs/ADR/0007
    latest_forecast: ForecastItem | None
