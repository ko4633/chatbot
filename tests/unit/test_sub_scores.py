from __future__ import annotations

import pytest

from packages.db.enums import RegulationStatus
from packages.scoring import sub_scores as ss


def test_demand_score_saturates_at_reference():
    assert ss.demand_score(ss.DEMAND_REFERENCE_REVIEW_COUNT) == pytest.approx(100.0, abs=0.01)


def test_demand_score_zero_reviews_is_zero():
    assert ss.demand_score(0) == 0.0


def test_competition_score_decreases_with_more_sellers():
    assert ss.competition_score(1) == 100.0
    assert ss.competition_score(2) == 75.0
    assert ss.competition_score(5) == 0.0  # clipped, not negative


def test_price_gap_score_hand_computed():
    # jp_krw_equiv=11904 (1280*9.3), target=12900
    # gap_pct = (12900-11904)/12900 = 0.07721
    # score = 100 * 0.07721 / 0.5 = 15.44
    score = ss.price_gap_score(1280 * 9.3, 12900)
    assert score == pytest.approx(15.44, abs=0.1)


def test_margin_score_zero_when_margin_not_positive():
    assert ss.margin_score(contribution_margin_rate=-0.1, contribution_margin_krw=-1000) == 0.0


def test_margin_score_scaled_down_below_absolute_floor():
    # rate alone would give 100*0.30/0.30=100, but margin_krw is far below
    # the MARGIN_ABSOLUTE_FLOOR_KRW floor, so it must be scaled down.
    low = ss.margin_score(contribution_margin_rate=0.30, contribution_margin_krw=2000)
    high = ss.margin_score(contribution_margin_rate=0.30, contribution_margin_krw=20000)
    assert low < high
    assert high == pytest.approx(100.0, abs=0.01)


def test_trend_score_rewards_price_drop():
    dropped = ss.trend_score(oldest_price=1580, newest_price=1280)
    risen = ss.trend_score(oldest_price=1280, newest_price=1580)
    assert dropped > 50
    assert risen < 50


def test_trend_score_neutral_without_history():
    assert ss.trend_score(None, 1280) == 50.0


def test_supply_score_zero_when_out_of_stock():
    assert ss.supply_score(in_stock=False, stock_quantity=100, jp_seller_count=3) == 0.0


def test_logistics_score_decreases_with_weight():
    light = ss.logistics_score(100)
    heavy = ss.logistics_score(1900)
    assert light > heavy


def test_logistics_score_neutral_when_missing():
    assert ss.logistics_score(None) == 50.0


def test_regulation_score_unknown_is_neutral_not_confident():
    assert ss.regulation_score(RegulationStatus.UNKNOWN) == 50.0
    assert ss.regulation_score(RegulationStatus.KNOWN_RESTRICTED) == 0.0
