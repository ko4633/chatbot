"""docs/ADR/0009: forecast direction is a deterministic label off a measured
delta, never a fabricated probability. These tests pin the classification
rule and confirm predicted_probability-shaped output never appears here."""

from __future__ import annotations

from packages.db.enums import ConfidenceTier, ForecastDirection
from packages.scoring.forecast import classify_forecast_direction


def test_no_prior_history_is_neutral_low_confidence():
    result = classify_forecast_direction(None, None, fx_is_stale=False)
    assert result.direction == ForecastDirection.NEUTRAL
    assert result.confidence_tier == ConfidenceTier.LOW
    assert "reason" in result.evidence


def test_rising_score_and_margin_is_bullish():
    result = classify_forecast_direction(score_delta=8.0, margin_delta_krw=500.0, fx_is_stale=False)
    assert result.direction == ForecastDirection.BULLISH


def test_falling_score_is_bearish():
    result = classify_forecast_direction(score_delta=-6.0, margin_delta_krw=100.0, fx_is_stale=False)
    assert result.direction == ForecastDirection.BEARISH


def test_falling_margin_is_bearish_even_with_flat_score():
    result = classify_forecast_direction(score_delta=1.0, margin_delta_krw=-100.0, fx_is_stale=False)
    assert result.direction == ForecastDirection.BEARISH


def test_small_moves_are_neutral():
    result = classify_forecast_direction(score_delta=1.0, margin_delta_krw=50.0, fx_is_stale=False)
    assert result.direction == ForecastDirection.NEUTRAL


def test_large_score_move_with_fresh_fx_is_high_confidence():
    result = classify_forecast_direction(score_delta=15.0, margin_delta_krw=500.0, fx_is_stale=False)
    assert result.confidence_tier == ConfidenceTier.HIGH


def test_stale_fx_caps_confidence_at_low_regardless_of_score_delta():
    result = classify_forecast_direction(score_delta=20.0, margin_delta_krw=1000.0, fx_is_stale=True)
    assert result.confidence_tier == ConfidenceTier.LOW


def test_moderate_score_move_is_medium_confidence():
    result = classify_forecast_direction(score_delta=6.0, margin_delta_krw=100.0, fx_is_stale=False)
    assert result.confidence_tier == ConfidenceTier.MEDIUM
