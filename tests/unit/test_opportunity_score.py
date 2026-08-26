from __future__ import annotations

import pytest

from packages.scoring.opportunity import compute_opportunity_score
from packages.scoring.sub_scores import SubScores


def test_opportunity_score_all_zero_is_zero():
    scores = SubScores(
        demand=0, competition=0, price_gap=0, margin=0, trend=0, supply=0, logistics=0, regulation=0
    )
    result = compute_opportunity_score(scores)
    assert result.score == 0.0


def test_opportunity_score_all_hundred_is_hundred():
    scores = SubScores(
        demand=100,
        competition=100,
        price_gap=100,
        margin=100,
        trend=100,
        supply=100,
        logistics=100,
        regulation=100,
    )
    result = compute_opportunity_score(scores)
    assert result.score == pytest.approx(100.0, abs=0.01)


def test_opportunity_score_weighted_sum_hand_computed():
    # Using config/opportunity_weights.yaml defaults:
    # demand .15, competition .15, price_gap .20, margin .20, trend .10,
    # supply .10, logistics .05, regulation .05
    scores = SubScores(
        demand=60,
        competition=100,
        price_gap=100,
        margin=48,
        trend=57,
        supply=75,
        logistics=87,
        regulation=50,
    )
    expected = (
        60 * 0.15
        + 100 * 0.15
        + 100 * 0.20
        + 48 * 0.20
        + 57 * 0.10
        + 75 * 0.10
        + 87 * 0.05
        + 50 * 0.05
    )
    result = compute_opportunity_score(scores)
    assert result.score == pytest.approx(expected, abs=0.01)


def test_confidence_is_never_a_weight_key():
    scores = SubScores(
        demand=1, competition=1, price_gap=1, margin=1, trend=1, supply=1, logistics=1, regulation=1
    )
    result = compute_opportunity_score(scores)
    assert "confidence" not in result.weighted_components
