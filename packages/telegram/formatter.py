"""Pure formatting only — no scoring, margin, or matching logic lives here
(docs/ADR/0010). Every number below was already computed by
packages/scoring/packages/intelligence; this module only turns it into text.
"""

from __future__ import annotations

from packages.db.models.opportunity import Opportunity


def format_opportunity_broadcast(
    opportunity: Opportunity,
    product_title: str,
    data_mode: str,
    why_now_narrative: str | None = None,
    counter_argument_narrative: str | None = None,
) -> str:
    econ = opportunity.economics
    fx_note = " (STALE)" if econ.get("fx_is_stale") else ""
    margin_rate = econ.get("contribution_margin_rate")
    margin_rate_pct = f"{margin_rate * 100:.1f}%" if margin_rate is not None else "n/a"

    lines = [
        f"New Opportunity: {product_title}",
        f"Score {opportunity.opportunity_score}/100 | Confidence {opportunity.confidence_score}/100",
        f"JP price: {econ.get('japan_purchase_price_jpy')} JPY -> KR price: {econ.get('target_sale_price_krw')} KRW",
        f"FX: {econ.get('jpy_krw_fx')}{fx_note}",
        f"Landed cost: {econ.get('landed_cost_krw')} KRW",
        f"Margin: {econ.get('contribution_margin_krw')} KRW ({margin_rate_pct})",
        f"Competition: {econ.get('kr_seller_count')} KR seller(s)",
    ]
    if why_now_narrative:
        lines.append(f"Why now: {why_now_narrative}")
    if counter_argument_narrative:
        lines.append(f"Risk: {counter_argument_narrative}")
    lines.append(f"Source data: {data_mode}")
    return "\n".join(lines)
