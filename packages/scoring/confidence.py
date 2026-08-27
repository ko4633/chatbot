"""Confidence Score — deliberately independent of the Opportunity Score
(ADR-0003, docs/AI_POLICY.md §5, docs/MASTER_SPEC.md §15). Answers "how much
should you trust this number", never "how good is this opportunity".
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from packages.core.time_utils import utcnow
from packages.db.enums import MatchType

# Named weights for each confidence input — tunable in one place, never
# inlined as unexplained numbers at the call site.
CONFIDENCE_COMPONENT_WEIGHTS = {
    "source_count": 0.15,
    "source_reliability": 0.15,
    "freshness": 0.15,
    "identifier_tier": 0.20,
    "completeness": 0.15,
    "ai_independence": 0.10,
    "fx_freshness": 0.10,
}

FRESHNESS_FULL_CONFIDENCE_DAYS = 7
FRESHNESS_ZERO_CONFIDENCE_DAYS = 90

IDENTIFIER_TIER_SCORE = {
    MatchType.EXACT: 100.0,
    MatchType.LIKELY: 70.0,
    MatchType.POSSIBLE: 40.0,
    MatchType.UNKNOWN: 10.0,
    MatchType.REJECTED: 0.0,
}

RELIABILITY_SCORE = {"LOW": 33.0, "MEDIUM": 66.0, "HIGH": 100.0}

# An opportunity's economics depend on the FX rate used to compute them
# (packages/scoring/margin.py); a stale FX observation means the margin
# figures may no longer reflect reality, so it lowers confidence in the
# number even though the product-side data hasn't changed (product brief §9).
FX_FRESH_SCORE = 100.0
FX_STALE_SCORE = 30.0


def _clip(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))


def _freshness_score(most_recent_observed_at: datetime) -> float:
    age_days = (utcnow() - most_recent_observed_at).total_seconds() / 86400
    if age_days <= FRESHNESS_FULL_CONFIDENCE_DAYS:
        return 100.0
    if age_days >= FRESHNESS_ZERO_CONFIDENCE_DAYS:
        return 0.0
    span = FRESHNESS_ZERO_CONFIDENCE_DAYS - FRESHNESS_FULL_CONFIDENCE_DAYS
    return _clip(100 * (1 - (age_days - FRESHNESS_FULL_CONFIDENCE_DAYS) / span))


@dataclass(frozen=True)
class ConfidenceInputs:
    distinct_source_count: int
    average_source_reliability: str  # "LOW" | "MEDIUM" | "HIGH"
    most_recent_observed_at: datetime
    entity_match_type: MatchType
    missing_field_count: int
    total_relevant_field_count: int
    ai_assisted_match: bool
    fx_is_stale: bool = False


@dataclass(frozen=True)
class ConfidenceResult:
    score: float
    components: dict = field(default_factory=dict)


def compute_confidence(inputs: ConfidenceInputs) -> ConfidenceResult:
    source_count_score = _clip(100 * inputs.distinct_source_count / 2)  # 2 markets = full credit
    reliability_score = RELIABILITY_SCORE.get(inputs.average_source_reliability, 50.0)
    freshness = _freshness_score(inputs.most_recent_observed_at)
    identifier_tier_score = IDENTIFIER_TIER_SCORE[inputs.entity_match_type]
    completeness_score = _clip(
        100 * (1 - inputs.missing_field_count / max(inputs.total_relevant_field_count, 1))
    )
    ai_independence_score = 60.0 if inputs.ai_assisted_match else 100.0
    fx_freshness_score = FX_STALE_SCORE if inputs.fx_is_stale else FX_FRESH_SCORE

    components = {
        "source_count": source_count_score,
        "source_reliability": reliability_score,
        "freshness": freshness,
        "identifier_tier": identifier_tier_score,
        "completeness": completeness_score,
        "ai_independence": ai_independence_score,
        "fx_freshness": fx_freshness_score,
    }
    total = sum(components[name] * weight for name, weight in CONFIDENCE_COMPONENT_WEIGHTS.items())
    return ConfidenceResult(
        score=round(total, 2), components={k: round(v, 2) for k, v in components.items()}
    )
