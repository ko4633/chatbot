"""Deterministic landed-cost / margin calculator. See docs/MASTER_SPEC.md
§16 — this is exactly the kind of arithmetic docs/AI_POLICY.md §3 forbids
delegating to AI. Every assumption is a named, configurable field (loaded
from config/margin_assumptions.yaml), never a magic number inline.
"""

from __future__ import annotations

from dataclasses import dataclass

from packages.scoring.config_loader import load_margin_assumptions


@dataclass(frozen=True)
class MarginAssumptions:
    jpy_krw_fx: float
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
    assumptions: MarginAssumptions


def compute_landed_cost_krw(
    japan_purchase_price_jpy: float, assumptions: MarginAssumptions
) -> float:
    fx = assumptions.jpy_krw_fx
    dutiable_value_jpy = (
        japan_purchase_price_jpy
        + assumptions.japan_domestic_shipping_jpy
        + assumptions.international_shipping_jpy_per_unit
        + assumptions.forwarding_fee_jpy_per_unit
    )
    dutiable_value_krw = dutiable_value_jpy * fx
    customs_duty_krw = dutiable_value_krw * assumptions.customs_duty_rate
    import_vat_krw = (dutiable_value_krw + customs_duty_krw) * assumptions.import_vat_rate
    return dutiable_value_krw + customs_duty_krw + import_vat_krw + assumptions.other_cost_krw


def compute_margin(
    japan_purchase_price_jpy: float,
    target_sale_price_krw: float,
    assumptions: MarginAssumptions | None = None,
) -> MarginResult:
    assumptions = assumptions or MarginAssumptions.from_config()
    landed_cost_krw = compute_landed_cost_krw(japan_purchase_price_jpy, assumptions)

    variable_rate = (
        assumptions.payment_fee_rate
        + assumptions.marketplace_commission_rate
        + assumptions.advertising_cost_assumption_rate
        + assumptions.return_allowance_rate
    )
    flat_fees_krw = assumptions.fulfillment_fee_krw_per_unit + assumptions.korean_delivery_fee_krw

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
        assumptions=assumptions,
    )
