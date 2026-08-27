"""Builds the "Why Now", "Counter-Argument", and "Missing Data" Insight rows
for an Opportunity. Narrative text for Why Now/Counter-Argument may be
AI-assisted (docs/AI_POLICY.md §2), but every number quoted in the
deterministic_fallback is pulled directly from the Opportunity's own
economics/sub_scores — the AI is asked to phrase facts already computed by
packages/scoring, never to compute or invent them. Missing Data is never
AI-assisted at all: it is a plain list of which tracked fields came back
null (packages/intelligence/opportunity_builder.py), and CLAUDE.md forbids
AI from filling in what it doesn't know — there is nothing for a model to
add here that isn't already a fabrication risk.
"""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from packages.ai.base import AIProvider
from packages.ai.types import GenerateRequest
from packages.db.enums import AIRunPurpose, InsightKind
from packages.db.models.insight import Insight
from packages.db.models.opportunity import Opportunity

PROMPT_VERSION = "insight_narrative.v1"


def _why_now_fallback(opp: Opportunity) -> str:
    econ = opp.economics
    return (
        f"JP purchase price {econ['japan_purchase_price_jpy']} JPY vs KR sale price "
        f"{econ['target_sale_price_krw']} KRW. Estimated contribution margin "
        f"{econ['contribution_margin_krw']} KRW ({econ['contribution_margin_rate'] * 100:.1f}%) "
        f"against {econ['kr_seller_count']} current KR seller(s). Opportunity score "
        f"{opp.opportunity_score}/100, confidence {opp.confidence_score}/100."
    )


def _counter_argument_fallback(opp: Opportunity) -> str:
    econ = opp.economics
    risks = []
    if econ["contribution_margin_krw"] <= 0:
        risks.append("Estimated contribution margin is zero or negative at current assumptions.")
    if econ["kr_seller_count"] >= 3:
        risks.append(f"{econ['kr_seller_count']} KR sellers already compete on this product.")
    if opp.confidence_score < 60:
        risks.append(
            f"Confidence is only {opp.confidence_score}/100 — treat the score as provisional."
        )
    if opp.regulation_status.value == "UNKNOWN":
        risks.append("Regulation/customs status is UNKNOWN, not confirmed low-risk.")
    if not risks:
        risks.append("No major deterministic red flags identified from available data alone.")
    return " ".join(risks)


_MISSING_FIELD_LABELS = {
    "jp_model_number": "JP model number",
    "jp_weight_g": "JP item weight",
    "kr_model_number": "KR model number",
    "review_count": "review count",
    "jp_stock_quantity": "JP stock quantity",
}


def _missing_data_narrative(opp: Opportunity) -> str:
    missing = opp.economics.get("missing_data_fields", [])
    if not missing:
        return "No missing data identified among the fields OMNIS tracks for this opportunity."
    labels = [_MISSING_FIELD_LABELS.get(f, f) for f in missing]
    return (
        f"Not available at collection time: {', '.join(labels)}. "
        "These fields would improve confidence if collected, but OMNIS does not "
        "estimate or infer them — see docs/AI_POLICY.md."
    )


def build_insights_for_opportunity(
    db: Session,
    ai_provider: AIProvider,
    opportunity: Opportunity,
    analysis_run_id: uuid.UUID | None,
) -> list[Insight]:
    insights = []
    for title, fallback_fn, purpose, kind in (
        ("Why Now", _why_now_fallback, AIRunPurpose.OPPORTUNITY_NARRATIVE, InsightKind.WHY_NOW),
        (
            "Counter-Argument",
            _counter_argument_fallback,
            AIRunPurpose.COUNTER_ARGUMENT,
            InsightKind.COUNTER_ARGUMENT,
        ),
    ):
        fallback = fallback_fn(opportunity)
        result = ai_provider.generate(
            db,
            GenerateRequest(
                purpose=purpose,
                prompt=f"Opportunity economics: {opportunity.economics}\nSub-scores: {opportunity.sub_scores}",
                prompt_version=PROMPT_VERSION,
                system=f"Write a concise 2-3 sentence '{title}' note for a product-import opportunity, "
                "using only the facts given. Do not invent numbers not present in the input.",
                deterministic_fallback=fallback,
                analysis_run_id=analysis_run_id,
            ),
        )
        insight = Insight(
            product_id=opportunity.product_id,
            kind=kind,
            title=title,
            narrative=result.text,
            supporting_facts=[{"table": "opportunity", "id": str(opportunity.id)}],
            is_ai_generated=result.ai_generated,
            ai_assisted_fields=["narrative"] if result.ai_generated else [],
            confidence=round(opportunity.confidence_score / 100, 3),
            analysis_run_id=analysis_run_id,
            retrieved_at=opportunity.retrieved_at,
            observed_at=opportunity.observed_at,
            extraction_method=opportunity.extraction_method,
            ai_run_id=result.ai_run_id,
        )
        db.add(insight)
        insights.append(insight)

    missing_data_insight = Insight(
        product_id=opportunity.product_id,
        kind=InsightKind.MISSING_DATA,
        title="Missing Data",
        narrative=_missing_data_narrative(opportunity),
        supporting_facts=[{"table": "opportunity", "id": str(opportunity.id)}],
        is_ai_generated=False,
        ai_assisted_fields=[],
        confidence=1.0,  # a list of which fields are null is a fact, not an estimate
        analysis_run_id=analysis_run_id,
        retrieved_at=opportunity.retrieved_at,
        observed_at=opportunity.observed_at,
        extraction_method=opportunity.extraction_method,
    )
    db.add(missing_data_insight)
    insights.append(missing_data_insight)

    db.flush()
    return insights
