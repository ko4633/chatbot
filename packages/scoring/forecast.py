"""Deterministic forecast direction classifier. Never a fabricated
probability — see docs/ADR/0009-forecast-no-fabricated-probability.md and
CLAUDE.md ("do not replace deterministic calculations with LLM output").

The only signal used is the measured delta between two consecutive
opportunity recomputes for the same product (opportunity_score and
contribution_margin_krw) — a real, already-computed number, not an
estimate. With no prior recompute to compare against, direction is always
NEUTRAL/LOW rather than guessed from a single snapshot.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from packages.db.enums import ConfidenceTier, ForecastDirection

# Points of opportunity_score change considered a directional move, not
# noise — mirrors OPPORTUNITY_SCORE_CHANGE_THRESHOLD's role in event
# detection (packages/intelligence/opportunity_builder.py).
SCORE_DELTA_BULLISH_THRESHOLD = 5.0
SCORE_DELTA_BEARISH_THRESHOLD = -5.0

# A score delta at least this large, with a fresh FX rate, is HIGH
# confidence; otherwise MEDIUM. A stale FX rate always caps confidence at
# LOW regardless of the score delta's size, since margin/score off a stale
# rate isn't a claim about current reality (docs/DATA_MODEL.md fx freshness).
HIGH_CONFIDENCE_SCORE_DELTA = 10.0

FORECAST_HORIZON_DAYS = 7  # arbitrary, documented, not tuned against outcomes yet
MODEL_NAME = "deterministic-rule.v1"


@dataclass(frozen=True)
class ForecastClassification:
    direction: ForecastDirection
    confidence_tier: ConfidenceTier
    evidence: dict = field(default_factory=dict)


def classify_forecast_direction(
    score_delta: float | None,
    margin_delta_krw: float | None,
    fx_is_stale: bool,
) -> ForecastClassification:
    if score_delta is None or margin_delta_krw is None:
        return ForecastClassification(
            direction=ForecastDirection.NEUTRAL,
            confidence_tier=ConfidenceTier.LOW,
            evidence={"reason": "no prior opportunity recompute to compare against"},
        )

    if score_delta >= SCORE_DELTA_BULLISH_THRESHOLD and margin_delta_krw > 0:
        direction = ForecastDirection.BULLISH
    elif score_delta <= SCORE_DELTA_BEARISH_THRESHOLD or margin_delta_krw < 0:
        direction = ForecastDirection.BEARISH
    else:
        direction = ForecastDirection.NEUTRAL

    if fx_is_stale:
        confidence_tier = ConfidenceTier.LOW
    elif abs(score_delta) >= HIGH_CONFIDENCE_SCORE_DELTA:
        confidence_tier = ConfidenceTier.HIGH
    else:
        confidence_tier = ConfidenceTier.MEDIUM

    return ForecastClassification(
        direction=direction,
        confidence_tier=confidence_tier,
        evidence={
            "score_delta": round(score_delta, 2),
            "margin_delta_krw": round(margin_delta_krw, 2),
            "fx_is_stale": fx_is_stale,
        },
    )
