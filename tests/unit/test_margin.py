"""docs/EVALUATION.md §3: expected values below were computed by hand from
config/margin_assumptions.yaml's defaults, not by running the function and
asserting on its own output.

jpy_krw_fx=9.30, japan_domestic_shipping_jpy=200,
international_shipping_jpy_per_unit=300, forwarding_fee_jpy_per_unit=150,
customs_duty_rate=0.08, import_vat_rate=0.10, other_cost_krw=500,
payment_fee_rate=0.023, marketplace_commission_rate=0.11,
fulfillment_fee_krw_per_unit=2500, korean_delivery_fee_krw=3000,
advertising_cost_assumption_rate=0.08, return_allowance_rate=0.02.
"""

from __future__ import annotations

import pytest

from packages.scoring.margin import (
    MarginAssumptions,
    compute_break_even_fx,
    compute_fx_sensitivity,
    compute_margin,
)

ASSUMPTIONS = MarginAssumptions.from_config()


def test_compute_margin_product_b_hand_computed():
    # dutiable_jpy = 5980 + 200 + 300 + 150 = 6630
    # dutiable_krw = 6630 * 9.30 = 61,659
    # customs = 61659 * 0.08 = 4,932.72
    # vat = (61659 + 4932.72) * 0.10 = 6,659.172
    # landed = 61659 + 4932.72 + 6659.172 + 500 = 73,750.892
    result = compute_margin(
        japan_purchase_price_jpy=5980,
        target_sale_price_krw=128000,
        fx_rate=9.30,
        assumptions=ASSUMPTIONS,
    )
    assert result.landed_cost_krw == pytest.approx(73750.892, abs=0.01)

    # variable_rate = 0.023 + 0.11 + 0.08 + 0.02 = 0.233
    # flat_fees = 2500 + 3000 = 5500
    # contribution_margin = 128000 - 73750.892 - 5500 - 0.233*128000
    #                      = 128000 - 73750.892 - 5500 - 29824 = 18,925.108
    assert result.contribution_margin_krw == pytest.approx(18925.108, abs=0.01)
    assert result.contribution_margin_rate == pytest.approx(18925.108 / 128000, abs=1e-6)

    # break_even = (landed_cost + flat_fees) / (1 - variable_rate)
    #            = (73750.892 + 5500) / 0.767 = 103,325.80...
    assert result.break_even_sale_price_krw == pytest.approx(103325.80, abs=0.5)


def test_compute_margin_negative_when_landed_cost_exceeds_sale_price():
    # Product A hand-computation: dutiable_jpy = 1280+200+300+150=1930
    # dutiable_krw = 1930*9.30 = 17,949; customs=1435.92; vat=1938.492
    # landed = 17949+1435.92+1938.492+500 = 21,823.412
    result = compute_margin(
        japan_purchase_price_jpy=1280,
        target_sale_price_krw=12900,
        fx_rate=9.30,
        assumptions=ASSUMPTIONS,
    )
    assert result.landed_cost_krw == pytest.approx(21823.412, abs=0.01)
    assert result.contribution_margin_krw < 0
    assert result.gross_profit_krw < 0


def test_compute_margin_zero_sale_price_does_not_divide_by_zero():
    result = compute_margin(
        japan_purchase_price_jpy=1000, target_sale_price_krw=0, fx_rate=9.30, assumptions=ASSUMPTIONS
    )
    assert result.contribution_margin_rate == 0.0


def test_higher_fx_rate_increases_landed_cost_and_lowers_margin():
    # FX must actually flow through to the same purchase/sale prices —
    # product brief §7: "환율이 바뀌면 상품 경제성이 자동으로 다시 계산될 수 있어야 한다".
    cheap_fx = compute_margin(
        japan_purchase_price_jpy=5980, target_sale_price_krw=128000, fx_rate=9.00, assumptions=ASSUMPTIONS
    )
    expensive_fx = compute_margin(
        japan_purchase_price_jpy=5980, target_sale_price_krw=128000, fx_rate=10.00, assumptions=ASSUMPTIONS
    )
    assert expensive_fx.landed_cost_krw > cheap_fx.landed_cost_krw
    assert expensive_fx.contribution_margin_krw < cheap_fx.contribution_margin_krw


def test_break_even_fx_yields_zero_contribution_margin():
    # compute_break_even_fx is a closed-form solve, not a search — verify it
    # against compute_margin itself rather than a second hand computation,
    # since the whole point is that plugging its output back in gives exactly
    # zero contribution margin.
    break_even = compute_break_even_fx(
        japan_purchase_price_jpy=5980, target_sale_price_krw=128000, assumptions=ASSUMPTIONS
    )
    result = compute_margin(
        japan_purchase_price_jpy=5980,
        target_sale_price_krw=128000,
        fx_rate=break_even,
        assumptions=ASSUMPTIONS,
    )
    assert result.contribution_margin_krw == pytest.approx(0.0, abs=0.5)


def test_fx_sensitivity_is_monotonically_decreasing_in_fx_rate():
    sensitivity = compute_fx_sensitivity(
        japan_purchase_price_jpy=5980,
        target_sale_price_krw=128000,
        current_fx_rate=9.30,
        fx_rate_deltas=(-0.30, 0.0, 0.30, 0.70),
        assumptions=ASSUMPTIONS,
    )
    ordered_rates = sorted(sensitivity)
    margins = [sensitivity[rate].contribution_margin_krw for rate in ordered_rates]
    assert margins == sorted(margins, reverse=True)


def test_fx_sensitivity_skips_non_positive_rates():
    sensitivity = compute_fx_sensitivity(
        japan_purchase_price_jpy=5980,
        target_sale_price_krw=128000,
        current_fx_rate=0.20,
        fx_rate_deltas=(-0.30, 0.0),
        assumptions=ASSUMPTIONS,
    )
    assert all(rate > 0 for rate in sensitivity)
