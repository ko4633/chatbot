"""Builds Opportunity rows for every canonical Product that has at least one
resolved JP offer and one resolved KR offer. Pure orchestration — all actual
arithmetic lives in packages/scoring (docs/AI_POLICY.md §3: scoring never
imports packages/ai, and this module never computes a score itself, only
gathers the facts scoring needs).

Phase 2: FX is fetched from packages/intelligence/facts (backed by
packages/fx observations), not a static config value — see
docs/ADR/0006-fx-provider-architecture.md and product brief §7.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy.orm import Session

from packages.core.settings import get_settings
from packages.core.time_utils import utcnow
from packages.db.enums import (
    DataQualityStatus,
    EventEntityType,
    EventType,
    ExtractionMethod,
    MatchStage,
    MatchType,
    OpportunityStatus,
    OpportunityType,
    RegulationStatus,
)
from packages.db.models.entity_match import EntityMatch
from packages.db.models.event import Event
from packages.db.models.forecast import Forecast
from packages.db.models.observations import PriceObservation
from packages.db.models.offer import Offer
from packages.db.models.opportunity import Opportunity
from packages.db.models.product import Product, ProductVariant
from packages.db.models.source import Source
from packages.intelligence import facts
from packages.observability.logging import get_logger
from packages.scoring import sub_scores as ss
from packages.scoring.confidence import ConfidenceInputs, compute_confidence
from packages.scoring.forecast import FORECAST_HORIZON_DAYS
from packages.scoring.forecast import MODEL_NAME as FORECAST_MODEL_NAME
from packages.scoring.forecast import classify_forecast_direction
from packages.scoring.margin import (
    MarginResult,
    compute_break_even_fx,
    compute_fx_sensitivity,
    compute_margin,
)
from packages.scoring.opportunity import compute_opportunity_score

logger = get_logger(__name__)

ALGORITHM_VERSION = "opportunity_builder.v2"
OPPORTUNITY_SCORE_CHANGE_THRESHOLD = 5.0  # points; below this, a recompute doesn't emit an event
FX_BASE_CURRENCY = "JPY"
FX_QUOTE_CURRENCY = "KRW"

_MATCH_TIER_RANK = {
    MatchType.EXACT: 4,
    MatchType.LIKELY: 3,
    MatchType.POSSIBLE: 2,
    MatchType.UNKNOWN: 1,
    MatchType.REJECTED: 0,
}


@dataclass
class OpportunityBuilderStats:
    opportunities_created: int = 0
    products_skipped_no_cross_market_offer: int = 0
    products_skipped_no_fx_data: int = 0


def _weakest_match_type(db: Session, product_id: uuid.UUID) -> MatchType:
    matches = db.query(EntityMatch).filter_by(resolved_product_id=product_id).all()
    if not matches:
        return MatchType.UNKNOWN
    return min((m.match_type for m in matches), key=lambda mt: _MATCH_TIER_RANK[mt])


def _any_ai_assisted(db: Session, product_id: uuid.UUID) -> bool:
    matches = db.query(EntityMatch).filter_by(resolved_product_id=product_id).all()
    return any(m.match_stage in (MatchStage.EMBEDDING, MatchStage.LLM_JUDGE) for m in matches)


_UNUSABLE_QUALITY_STATUSES = (DataQualityStatus.FAILED, DataQualityStatus.QUARANTINED)


def _is_source_usable(db: Session, source_id: uuid.UUID | None) -> bool:
    """A FAILED or QUARANTINED collector run must not feed the Opportunity
    calculation (product brief §16) — DEGRADED/STALE still pass through
    (lower confidence via freshness, not exclusion) since the data may still
    be directionally usable."""
    if source_id is None:
        return True
    source = db.get(Source, source_id)
    return source is None or source.data_quality_status not in _UNUSABLE_QUALITY_STATUSES


def _offers_for_market(db: Session, product_id: uuid.UUID, market_code: str) -> list[Offer]:
    from packages.db.models.catalog import Market  # local import avoids a module-level cycle

    variants = db.query(ProductVariant).filter_by(product_id=product_id).all()
    result = []
    for v in variants:
        market = db.get(Market, v.market_id)
        if market and market.code == market_code:
            result.extend(db.query(Offer).filter_by(product_variant_id=v.id).all())
    return result


def _previous_opportunity(db: Session, product_id: uuid.UUID) -> Opportunity | None:
    return (
        db.query(Opportunity)
        .filter(Opportunity.product_id == product_id, Opportunity.status != OpportunityStatus.STALE)
        .order_by(Opportunity.created_at.desc())
        .first()
    )


def build_opportunities(db: Session, analysis_run_id: uuid.UUID) -> OpportunityBuilderStats:
    stats = OpportunityBuilderStats()
    settings = get_settings()

    fx_observation = facts.latest_fx(db, FX_BASE_CURRENCY, FX_QUOTE_CURRENCY)
    if fx_observation is None:
        logger.error("no_fx_data_available", pair=f"{FX_BASE_CURRENCY}/{FX_QUOTE_CURRENCY}")
        stats.products_skipped_no_fx_data = db.query(Product).count()
        return stats
    fx_rate = float(fx_observation.rate)
    fx_is_stale = facts.is_fx_stale(fx_observation, settings.fx_stale_hours)

    for product in db.query(Product).all():
        jp_offers = _offers_for_market(db, product.id, "JP")
        kr_offers = _offers_for_market(db, product.id, "KR")
        if not jp_offers or not kr_offers:
            stats.products_skipped_no_cross_market_offer += 1
            continue

        jp_with_prices = [(o, facts.latest_price(db, o.id)) for o in jp_offers]
        jp_latest: list[tuple[Offer, PriceObservation]] = [
            (o, p) for o, p in jp_with_prices if p is not None and _is_source_usable(db, p.source_id)
        ]
        kr_with_prices = [(o, facts.latest_price(db, o.id)) for o in kr_offers]
        kr_latest: list[tuple[Offer, PriceObservation]] = [
            (o, p) for o, p in kr_with_prices if p is not None and _is_source_usable(db, p.source_id)
        ]
        if not jp_latest or not kr_latest:
            stats.products_skipped_no_cross_market_offer += 1
            continue

        cheapest_jp_offer, jp_price_obs = min(jp_latest, key=lambda pair: pair[1].price_amount)
        cheapest_kr_offer, kr_price_obs = min(kr_latest, key=lambda pair: pair[1].price_amount)

        jp_history = facts.price_history(db, cheapest_jp_offer.id)
        oldest_jp_price = jp_history[0].price_amount if jp_history else None
        newest_jp_price = jp_history[-1].price_amount if jp_history else None

        jp_inventory = facts.latest_inventory(db, cheapest_jp_offer.id)
        jp_variant = db.get(ProductVariant, cheapest_jp_offer.product_variant_id)
        kr_variant = db.get(ProductVariant, cheapest_kr_offer.product_variant_id)

        kr_in_stock_offers = [
            o
            for o, p in kr_latest
            if (inv := facts.latest_inventory(db, o.id)) is None or inv.in_stock
        ]
        kr_seller_count = len({o.seller_id for o in kr_in_stock_offers}) or len(kr_latest)
        jp_seller_count = len({o.seller_id for o in jp_offers})

        total_review_count = 0
        for variant in (jp_variant, kr_variant):
            review = facts.latest_review_stats(db, variant.id) if variant else None
            if review:
                total_review_count += review.review_count

        margin: MarginResult = compute_margin(
            japan_purchase_price_jpy=jp_price_obs.price_amount,
            target_sale_price_krw=kr_price_obs.price_amount,
            fx_rate=fx_rate,
        )
        fx_sensitivity = compute_fx_sensitivity(
            japan_purchase_price_jpy=jp_price_obs.price_amount,
            target_sale_price_krw=kr_price_obs.price_amount,
            current_fx_rate=fx_rate,
            assumptions=margin.assumptions,
        )

        regulation_status = RegulationStatus.UNKNOWN  # no regulation source integrated yet

        sub_scores = ss.SubScores(
            demand=ss.demand_score(total_review_count),
            competition=ss.competition_score(kr_seller_count),
            price_gap=ss.price_gap_score(
                jp_price_obs.price_amount * fx_rate, kr_price_obs.price_amount
            ),
            margin=ss.margin_score(margin.contribution_margin_rate, margin.contribution_margin_krw),
            trend=ss.trend_score(oldest_jp_price, newest_jp_price),
            supply=ss.supply_score(
                jp_inventory.in_stock if jp_inventory else True,
                jp_inventory.stock_quantity if jp_inventory else None,
                jp_seller_count,
            ),
            logistics=ss.logistics_score(jp_variant.weight_g if jp_variant else None),
            regulation=ss.regulation_score(regulation_status),
        )
        score_result = compute_opportunity_score(sub_scores)

        distinct_sources = {jp_price_obs.source_id, kr_price_obs.source_id}
        source_rows = [db.get(Source, sid) for sid in distinct_sources]
        reliabilities = [s.factual_reliability.value for s in source_rows if s is not None]
        worst_reliability = (
            min(reliabilities, key=lambda r: {"LOW": 0, "MEDIUM": 1, "HIGH": 2}[r])
            if reliabilities
            else "MEDIUM"
        )

        relevant_field_values = {
            "jp_model_number": jp_variant.model_number if jp_variant else None,
            "jp_weight_g": jp_variant.weight_g if jp_variant else None,
            "kr_model_number": kr_variant.model_number if kr_variant else None,
            "review_count": total_review_count or None,
            "jp_stock_quantity": jp_inventory.stock_quantity if jp_inventory else None,
        }
        missing_data_fields = [name for name, value in relevant_field_values.items() if value is None]
        relevant_fields = list(relevant_field_values.values())
        missing = len(missing_data_fields)

        confidence_result = compute_confidence(
            ConfidenceInputs(
                distinct_source_count=len(distinct_sources),
                average_source_reliability=worst_reliability,
                most_recent_observed_at=max(jp_price_obs.observed_at, kr_price_obs.observed_at),
                entity_match_type=_weakest_match_type(db, product.id),
                missing_field_count=missing,
                total_relevant_field_count=len(relevant_fields),
                ai_assisted_match=_any_ai_assisted(db, product.id),
                fx_is_stale=fx_is_stale,
            )
        )

        previous = _previous_opportunity(db, product.id)
        score_delta: float | None = None
        margin_delta_krw: float | None = None
        if previous is not None:
            previous.status = OpportunityStatus.STALE
            score_delta = score_result.score - float(previous.opportunity_score)
            previous_margin_for_delta = previous.economics.get("contribution_margin_krw")
            if previous_margin_for_delta is not None:
                margin_delta_krw = margin.contribution_margin_krw - previous_margin_for_delta
            if abs(score_delta) >= OPPORTUNITY_SCORE_CHANGE_THRESHOLD:
                same_product_inputs = (
                    previous.economics.get("japan_purchase_price_jpy") == jp_price_obs.price_amount
                    and previous.economics.get("target_sale_price_krw") == kr_price_obs.price_amount
                )
                fx_changed = previous.economics.get("jpy_krw_fx") != fx_rate
                is_fx_driven = same_product_inputs and fx_changed and score_delta > 0
                db.add(
                    Event(
                        entity_type=EventEntityType.PRODUCT,
                        entity_id=product.id,
                        event_type=EventType.FX_DRIVEN_OPPORTUNITY
                        if is_fx_driven
                        else EventType.OPPORTUNITY_SCORE_CHANGE,
                        previous_value={
                            "opportunity_score": float(previous.opportunity_score),
                            "jpy_krw_fx": previous.economics.get("jpy_krw_fx"),
                        },
                        new_value={"opportunity_score": score_result.score, "jpy_krw_fx": fx_rate},
                        change_pct=round(
                            score_delta / max(float(previous.opportunity_score), 1) * 100, 2
                        ),
                        observed_at=utcnow(),
                        evidence={"previous_opportunity_id": str(previous.id)},
                        confidence=1.0,
                        analysis_run_id=analysis_run_id,
                    )
                )

            # MARGIN_THRESHOLD_CROSSED: the one deterministic, business-
            # meaningful threshold that needs no tunable config — margin
            # rate crossing zero (profitable <-> unprofitable), independent
            # of whether the opportunity score moved enough to also fire
            # OPPORTUNITY_SCORE_CHANGE above (product brief §6).
            previous_margin_krw = previous.economics.get("contribution_margin_krw")
            if (
                previous_margin_krw is not None
                and previous_margin_krw != 0
                and (previous_margin_krw > 0) != (margin.contribution_margin_krw > 0)
            ):
                db.add(
                    Event(
                        entity_type=EventEntityType.PRODUCT,
                        entity_id=product.id,
                        event_type=EventType.MARGIN_THRESHOLD_CROSSED,
                        previous_value={"contribution_margin_krw": previous_margin_krw},
                        new_value={"contribution_margin_krw": round(margin.contribution_margin_krw, 2)},
                        change_pct=None,
                        observed_at=utcnow(),
                        evidence={"previous_opportunity_id": str(previous.id)},
                        confidence=1.0,
                        analysis_run_id=analysis_run_id,
                    )
                )

        forecast_classification = classify_forecast_direction(
            score_delta=score_delta, margin_delta_krw=margin_delta_krw, fx_is_stale=fx_is_stale
        )
        db.add(
            Forecast(
                product_id=product.id,
                analysis_run_id=analysis_run_id,
                forecast_created_at=utcnow(),
                forecast_horizon_days=FORECAST_HORIZON_DAYS,
                predicted_direction=forecast_classification.direction,
                predicted_probability=None,  # never fabricated — docs/ADR/0009
                confidence_tier=forecast_classification.confidence_tier,
                is_calibrated=False,
                model=FORECAST_MODEL_NAME,
                evidence=forecast_classification.evidence,
            )
        )

        observed_at = max(jp_price_obs.observed_at, kr_price_obs.observed_at)
        opportunity = Opportunity(
            product_id=product.id,
            opportunity_type=OpportunityType.IMPORT_RESALE,
            opportunity_score=score_result.score,
            confidence_score=confidence_result.score,
            sub_scores={
                "weighted_components": score_result.weighted_components,
                "confidence_components": confidence_result.components,
            },
            weights_version=score_result.weights_version,
            economics={
                "japan_purchase_price_jpy": jp_price_obs.price_amount,
                "target_sale_price_krw": kr_price_obs.price_amount,
                "jpy_krw_fx": fx_rate,
                "fx_is_stale": fx_is_stale,
                "fx_observed_at": fx_observation.observed_at.isoformat(),
                "break_even_fx": round(
                    compute_break_even_fx(
                        japan_purchase_price_jpy=jp_price_obs.price_amount,
                        target_sale_price_krw=kr_price_obs.price_amount,
                        assumptions=margin.assumptions,
                    ),
                    4,
                ),
                "fx_sensitivity": {
                    str(rate): round(result.contribution_margin_krw, 2)
                    for rate, result in fx_sensitivity.items()
                },
                "landed_cost_krw": round(margin.landed_cost_krw, 2),
                "gross_profit_krw": round(margin.gross_profit_krw, 2),
                "contribution_margin_krw": round(margin.contribution_margin_krw, 2),
                "contribution_margin_rate": round(margin.contribution_margin_rate, 4),
                "break_even_sale_price_krw": round(margin.break_even_sale_price_krw, 2),
                "jp_offer_id": str(cheapest_jp_offer.id),
                "kr_offer_id": str(cheapest_kr_offer.id),
                "kr_seller_count": kr_seller_count,
                "jp_seller_count": jp_seller_count,
                "missing_data_fields": missing_data_fields,
            },
            regulation_status=regulation_status,
            regulation_basis="No official regulation/customs source integrated yet (docs/MASTER_SPEC.md §17).",
            status=OpportunityStatus.NEW if previous is None else OpportunityStatus.ACTIVE,
            analysis_run_id=analysis_run_id,
            retrieved_at=observed_at,
            observed_at=observed_at,
            extraction_method=ExtractionMethod.DERIVED,
            confidence=round(confidence_result.score / 100, 3),
        )
        db.add(opportunity)
        db.flush()
        stats.opportunities_created += 1

    return stats
