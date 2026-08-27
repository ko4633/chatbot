"""Deterministic 0-100 sub-scores feeding the Opportunity Score. No AI here
(docs/AI_POLICY.md §3) — every input is a fact already in the database.
Reference constants are named, not magic numbers, and are the sanctioned
place to tune scoring sensitivity (docs CLAUDE.md: no unexplained magic
numbers).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from packages.db.enums import RegulationStatus

# Reference points calibrate the 0-100 scale; each is independently tunable.
DEMAND_REFERENCE_REVIEW_COUNT = 1000  # review_count at which demand_score saturates at 100
COMPETITION_STEP_PENALTY = 25  # score lost per additional competing KR seller beyond the first
PRICE_GAP_REFERENCE_PCT = 0.5  # a 50% pre-fee price gap saturates price_gap_score at 100
MARGIN_REFERENCE_RATE = 0.30  # a 30% contribution margin rate saturates margin_score at 100
MARGIN_ABSOLUTE_FLOOR_KRW = 20_000  # below this absolute margin, margin_score is scaled down
TREND_PRICE_CHANGE_SENSITIVITY = 200  # multiplier converting a JP price change % into score delta
SUPPLY_REFERENCE_STOCK_QTY = 10  # JP stock_quantity at which supply_score saturates at 100
LOGISTICS_REFERENCE_WEIGHT_G = 2000  # weight at which logistics_score bottoms out at 0
REGULATION_SCORE_BY_STATUS = {
    RegulationStatus.UNKNOWN: 50.0,
    RegulationStatus.LIKELY_LOW: 90.0,
    RegulationStatus.REVIEW_REQUIRED: 30.0,
    RegulationStatus.KNOWN_RESTRICTED: 0.0,
}


def _clip(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))


def demand_score(total_review_count: int) -> float:
    if total_review_count <= 0:
        return 0.0
    return _clip(
        100 * math.log10(total_review_count + 1) / math.log10(DEMAND_REFERENCE_REVIEW_COUNT + 1)
    )


def competition_score(kr_seller_count: int) -> float:
    if kr_seller_count <= 0:
        return 100.0  # no current KR seller at all — maximally open field
    return _clip(100 - (kr_seller_count - 1) * COMPETITION_STEP_PENALTY)


def price_gap_score(japan_purchase_price_krw_equiv: float, target_sale_price_krw: float) -> float:
    if target_sale_price_krw <= 0:
        return 0.0
    gap_pct = (target_sale_price_krw - japan_purchase_price_krw_equiv) / target_sale_price_krw
    return _clip(100 * gap_pct / PRICE_GAP_REFERENCE_PCT)


def margin_score(contribution_margin_rate: float, contribution_margin_krw: float) -> float:
    if contribution_margin_krw <= 0:
        return 0.0
    base = _clip(100 * contribution_margin_rate / MARGIN_REFERENCE_RATE)
    floor_factor = min(1.0, contribution_margin_krw / MARGIN_ABSOLUTE_FLOOR_KRW)
    return _clip(base * floor_factor)


def trend_score(oldest_price: float | None, newest_price: float | None) -> float:
    if not oldest_price or not newest_price or oldest_price <= 0:
        return 50.0  # no history available — neutral, not a guess in either direction
    change_pct = (newest_price - oldest_price) / oldest_price
    return _clip(50 - change_pct * TREND_PRICE_CHANGE_SENSITIVITY)


def supply_score(in_stock: bool, stock_quantity: int | None, jp_seller_count: int) -> float:
    if not in_stock:
        return 0.0
    qty_component = (
        100.0
        if stock_quantity is None
        else _clip(100 * stock_quantity / SUPPLY_REFERENCE_STOCK_QTY)
    )
    seller_component = _clip(50 + (jp_seller_count - 1) * 25, 0, 100)
    return _clip((qty_component + seller_component) / 2)


def logistics_score(weight_g: int | None) -> float:
    if weight_g is None:
        return 50.0  # unknown — neutral, penalized separately via confidence, not guessed here
    return _clip(100 * (1 - weight_g / LOGISTICS_REFERENCE_WEIGHT_G))


def regulation_score(status: RegulationStatus) -> float:
    return REGULATION_SCORE_BY_STATUS[status]


@dataclass(frozen=True)
class SubScores:
    demand: float
    competition: float
    price_gap: float
    margin: float
    trend: float
    supply: float
    logistics: float
    regulation: float

    def as_dict(self) -> dict:
        return {
            "demand": round(self.demand, 2),
            "competition": round(self.competition, 2),
            "price_gap": round(self.price_gap, 2),
            "margin": round(self.margin, 2),
            "trend": round(self.trend, 2),
            "supply": round(self.supply, 2),
            "logistics": round(self.logistics, 2),
            "regulation": round(self.regulation, 2),
        }
