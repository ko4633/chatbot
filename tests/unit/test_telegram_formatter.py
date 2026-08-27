"""Pure formatting only (docs/ADR/0010) — every number in the output must
trace back to a field already present in Opportunity.economics, never
computed here."""

from __future__ import annotations

from packages.telegram.formatter import format_opportunity_broadcast


class _FakeOpportunity:
    opportunity_score = 82.5
    confidence_score = 71.0
    status = type("S", (), {"value": "NEW"})()
    economics = {
        "japan_purchase_price_jpy": 5980,
        "target_sale_price_krw": 128000,
        "jpy_krw_fx": 9.3,
        "fx_is_stale": False,
        "landed_cost_krw": 73750.89,
        "contribution_margin_krw": 18925.11,
        "contribution_margin_rate": 0.1479,
        "kr_seller_count": 2,
    }


def test_broadcast_includes_score_confidence_and_prices():
    text = format_opportunity_broadcast(_FakeOpportunity(), "Test Product", "mock")
    assert "82.5" in text
    assert "71.0" in text
    assert "5980" in text
    assert "128000" in text
    assert "Test Product" in text


def test_broadcast_flags_stale_fx():
    opp = _FakeOpportunity()
    opp.economics = {**opp.economics, "fx_is_stale": True}
    text = format_opportunity_broadcast(opp, "Test Product", "mock")
    assert "STALE" in text


def test_broadcast_includes_why_now_and_risk_when_given():
    text = format_opportunity_broadcast(
        _FakeOpportunity(),
        "Test Product",
        "mock",
        why_now_narrative="Great margin.",
        counter_argument_narrative="High competition.",
    )
    assert "Great margin." in text
    assert "High competition." in text


def test_broadcast_omits_why_now_and_risk_when_absent():
    text = format_opportunity_broadcast(_FakeOpportunity(), "Test Product", "mock")
    assert "Why now:" not in text
    assert "Risk:" not in text


def test_broadcast_includes_data_mode():
    text = format_opportunity_broadcast(_FakeOpportunity(), "Test Product", "live")
    assert "live" in text
