"""Deterministic pieces of insight_builder.py — the parts that must never
depend on an AI call (docs/AI_POLICY.md §3/§4, CLAUDE.md "AI must never fill
in what it doesn't know"). Missing Data is fact-only: a list of which
tracked fields came back null, nothing inferred.
"""

from __future__ import annotations

from packages.intelligence.insight_builder import _missing_data_narrative


class _FakeOpportunity:
    def __init__(self, missing_data_fields):
        self.economics = {"missing_data_fields": missing_data_fields}


def test_missing_data_narrative_lists_known_fields_by_label():
    narrative = _missing_data_narrative(_FakeOpportunity(["jp_model_number", "review_count"]))
    assert "JP model number" in narrative
    assert "review count" in narrative


def test_missing_data_narrative_falls_back_to_raw_name_for_unknown_field():
    narrative = _missing_data_narrative(_FakeOpportunity(["some_future_field"]))
    assert "some_future_field" in narrative


def test_missing_data_narrative_says_nothing_missing_when_empty():
    narrative = _missing_data_narrative(_FakeOpportunity([]))
    assert "No missing data" in narrative


def test_missing_data_narrative_never_invents_a_value_for_a_missing_field():
    # The narrative must name that a field is absent, never guess what its
    # value might have been — there is no "estimated" or numeric content here.
    narrative = _missing_data_narrative(_FakeOpportunity(["jp_stock_quantity"]))
    assert "estimate" not in narrative.lower() or "does not estimate" in narrative.lower()
