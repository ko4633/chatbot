"""Deterministic landed-cost / margin calculator. See docs/MASTER_SPEC.md
§16 — this is exactly the kind of arithmetic docs/AI_POLICY.md §3 forbids
delegating to AI. Every assumption is a named, configurable field (loaded
from config/margin_assumptions.yaml), never a magic number inline.

`fx_rate` is an explicit argument, not part of MarginAssumptions — FX is
observed, time-varying data (packages/fx), not a static assumption, per
docs/ADR/0006-fx-provider-architecture.md and product brief §7 ("환율이
바뀌면 상품 경제성이 자동으로 다시 계산될 수 있어야 한다").
"""

from __future__ import annotations

from dataclasses import dataclass

from packages.scoring.config_loader import load_margin_assumptions


@dataclass(frozen=True)
class MarginAssumptions:
    japan_domestic_shipping_jpy: float
    international_shipping_jpy_per_unit: float
    forwarding_fee_jpy_per_unit: float
    customs_duty_rate: float
    import_vat_rate: float
    payment_fee_rate: float
    marketplace_commission_rate: float
    fulfillment_fee_krw_per_unit: float
    korean_delivery_fee_krw: float
    advertising_cost_assumption_rate: float
    return_allowance_rate: float
    other_cost_krw: float

    @classmethod
    def from_config(cls) -> MarginAssumptions:
        return cls(**load_margin_assumptions())


@dataclass(frozen=True)
class MarginResult:
    landed_cost_krw: float
    gross_profit_krw: float
    contribution_margin_krw: float
    contribution_margin_rate: float
    break_even_sale_price_krw: float
    fx_rate: float
    assumptions: MarginAssumptions


def _dutiable_value_jpy(japan_purchase_price_jpy: float, assumptions: MarginAssumptions) -> float:
    return (
        japan_purchase_price_jpy
        + assumptions.japan_domestic_shipping_jpy
        + assumptions.international_shipping_jpy_per_unit
        + assumptions.forwarding_fee_jpy_per_unit
    )


def compute_landed_cost_krw(
    japan_purchase_price_jpy: float, fx_rate: float, assumptions: MarginAssumptions
) -> float:
    dutiable_value_jpy = _dutiable_value_jpy(japan_purchase_price_jpy, assumptions)
    dutiable_value_krw = dutiable_value_jpy * fx_rate
    customs_duty_krw = dutiable_value_krw * assumptions.customs_duty_rate
    import_vat_krw = (dutiable_value_krw + customs_duty_krw) * assumptions.import_vat_rate
    return dutiable_value_krw + customs_duty_krw + import_vat_krw + assumptions.other_cost_krw


def _variable_rate(assumptions: MarginAssumptions) -> float:
    return (
        assumptions.payment_fee_rate
        + assumptions.marketplace_commission_rate
        + assumptions.advertising_cost_assumption_rate
        + assumptions.return_allowance_rate
    )


def _flat_fees_krw(assumptions: MarginAssumptions) -> float:
    return assumptions.fulfillment_fee_krw_per_unit + assumptions.korean_delivery_fee_krw


def compute_margin(
    japan_purchase_price_jpy: float,
    target_sale_price_krw: float,
    fx_rate: float,
    assumptions: MarginAssumptions | None = None,
) -> MarginResult:
    assumptions = assumptions or MarginAssumptions.from_config()
    landed_cost_krw = compute_landed_cost_krw(japan_purchase_price_jpy, fx_rate, assumptions)

    variable_rate = _variable_rate(assumptions)
    flat_fees_krw = _flat_fees_krw(assumptions)

    gross_profit_krw = target_sale_price_krw - landed_cost_krw
    contribution_margin_krw = (
        target_sale_price_krw
        - landed_cost_krw
        - flat_fees_krw
        - variable_rate * target_sale_price_krw
    )
    contribution_margin_rate = (
        contribution_margin_krw / target_sale_price_krw if target_sale_price_krw > 0 else 0.0
    )

    denominator = 1 - variable_rate
    break_even_sale_price_krw = (
        (landed_cost_krw + flat_fees_krw) / denominator if denominator > 0 else float("inf")
    )

    return MarginResult(
        landed_cost_krw=landed_cost_krw,
        gross_profit_krw=gross_profit_krw,
        contribution_margin_krw=contribution_margin_krw,
        contribution_margin_rate=contribution_margin_rate,
        break_even_sale_price_krw=break_even_sale_price_krw,
        fx_rate=fx_rate,
        assumptions=assumptions,
    )


def compute_break_even_fx(
    japan_purchase_price_jpy: float,
    target_sale_price_krw: float,
    assumptions: MarginAssumptions | None = None,
) -> float:
    """The FX rate at which contribution_margin_krw == 0, holding JP price
    and KR sale price fixed (product brief §8). Closed-form, not iterative:
    contribution_margin is linear in fx_rate because landed_cost is linear
    in fx_rate (duty/VAT are both simple multiplicative rates on top of the
    fx-converted dutiable value), so this solves exactly rather than
    searching.
    """
    assumptions = assumptions or MarginAssumptions.from_config()
    dutiable_value_jpy = _dutiable_value_jpy(japan_purchase_price_jpy, assumptions)
    # landed_cost(fx) = A * fx + B
    a = dutiable_value_jpy * (1 + assumptions.customs_duty_rate) * (1 + assumptions.import_vat_rate)
    b = assumptions.other_cost_krw
    variable_rate = _variable_rate(assumptions)
    flat_fees_krw = _flat_fees_krw(assumptions)
    # contribution_margin(fx) = target*(1-variable_rate) - flat_fees - B - A*fx = 0
    numerator = target_sale_price_krw * (1 - variable_rate) - flat_fees_krw - b
    if a <= 0:
        return float("inf")
    return numerator / a


def compute_fx_sensitivity(
    japan_purchase_price_jpy: float,
    target_sale_price_krw: float,
    current_fx_rate: float,
    fx_rate_deltas: tuple[float, ...] = (-0.30, -0.10, 0.0, 0.10, 0.30, 0.70),
    assumptions: MarginAssumptions | None = None,
) -> dict[float, MarginResult]:
    """Margin at a range of FX rates around the current one (product brief
    §8: "9.00일 때, 9.50일 때, 10.00일 때 예상이익"). Deterministic — never
    delegated to AI (docs/AI_POLICY.md §3)."""
    assumptions = assumptions or MarginAssumptions.from_config()
    results = {}
    for delta in fx_rate_deltas:
        fx = round(current_fx_rate + delta, 4)
        if fx <= 0:
            continue
        results[fx] = compute_margin(japan_purchase_price_jpy, target_sale_price_krw, fx, assumptions)
    return results
