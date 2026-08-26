from __future__ import annotations

from datetime import timedelta

from packages.core.time_utils import utcnow
from packages.db.enums import MatchType
from packages.scoring.confidence import ConfidenceInputs, compute_confidence


def _inputs(**overrides) -> ConfidenceInputs:
    base = dict(
        distinct_source_count=2,
        average_source_reliability="MEDIUM",
        most_recent_observed_at=utcnow(),
        entity_match_type=MatchType.EXACT,
        missing_field_count=0,
        total_relevant_field_count=5,
        ai_assisted_match=False,
    )
    base.update(overrides)
    return ConfidenceInputs(**base)


def test_exact_match_scores_higher_than_likely():
    exact = compute_confidence(_inputs(entity_match_type=MatchType.EXACT))
    likely = compute_confidence(_inputs(entity_match_type=MatchType.LIKELY))
    assert exact.score > likely.score


def test_stale_data_reduces_confidence():
    fresh = compute_confidence(_inputs(most_recent_observed_at=utcnow()))
    stale = compute_confidence(_inputs(most_recent_observed_at=utcnow() - timedelta(days=120)))
    assert fresh.score > stale.score


def test_ai_assisted_match_scores_lower_than_deterministic():
    deterministic = compute_confidence(_inputs(ai_assisted_match=False))
    ai_assisted = compute_confidence(_inputs(ai_assisted_match=True))
    assert deterministic.score > ai_assisted.score


def test_missing_fields_reduce_confidence():
    complete = compute_confidence(_inputs(missing_field_count=0))
    incomplete = compute_confidence(_inputs(missing_field_count=5, total_relevant_field_count=5))
    assert complete.score > incomplete.score


def test_score_bounded_0_to_100():
    result = compute_confidence(_inputs())
    assert 0.0 <= result.score <= 100.0
