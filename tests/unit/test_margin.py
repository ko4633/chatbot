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

from packages.scoring.margin import MarginAssumptions, compute_margin

ASSUMPTIONS = MarginAssumptions.from_config()


def test_compute_margin_product_b_hand_computed():
    # dutiable_jpy = 5980 + 200 + 300 + 150 = 6630
    # dutiable_krw = 6630 * 9.30 = 61,659
    # customs = 61659 * 0.08 = 4,932.72
    # vat = (61659 + 4932.72) * 0.10 = 6,659.172
    # landed = 61659 + 4932.72 + 6659.172 + 500 = 73,750.892
    result = compute_margin(
        japan_purchase_price_jpy=5980, target_sale_price_krw=128000, assumptions=ASSUMPTIONS
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
        japan_purchase_price_jpy=1280, target_sale_price_krw=12900, assumptions=ASSUMPTIONS
    )
    assert result.landed_cost_krw == pytest.approx(21823.412, abs=0.01)
    assert result.contribution_margin_krw < 0
    assert result.gross_profit_krw < 0


def test_compute_margin_zero_sale_price_does_not_divide_by_zero():
    result = compute_margin(
        japan_purchase_price_jpy=1000, target_sale_price_krw=0, assumptions=ASSUMPTIONS
    )
    assert result.contribution_margin_rate == 0.0
