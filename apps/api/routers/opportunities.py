from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from apps.api.deps import get_db
from apps.api.schemas.common import PriceHistoryPoint, SourceRef
from apps.api.schemas.opportunity import (
    EntityMatchEvidenceItem,
    EventItem,
    ForecastItem,
    InsightItem,
    OpportunityDetail,
    OpportunityHistoryPoint,
    OpportunityHistoryResponse,
    OpportunityListItem,
    OpportunityListResponse,
    UserDecisionCreate,
    UserDecisionItem,
)
from packages.db.enums import DataMode, DecisionType, EventEntityType, OpportunityStatus
from packages.db.models.catalog import Market, Seller
from packages.db.models.decision import UserDecision
from packages.db.models.entity_match import EntityMatch
from packages.db.models.event import Event
from packages.db.models.forecast import Forecast
from packages.db.models.insight import Insight
from packages.db.models.offer import Offer
from packages.db.models.opportunity import Opportunity
from packages.db.models.product import Product, ProductVariant
from packages.db.models.source import Source
from packages.intelligence import facts
from packages.intelligence.system_status import system_data_mode

router = APIRouter(prefix="/opportunities", tags=["opportunities"])


def _opportunity_data_mode(sources: list[SourceRef]) -> str:
    """Per-opportunity rollup of Source.data_mode, mirroring _data_mode()'s
    system-wide version but scoped to only the sources actually backing this
    opportunity's data (docs/ADR/0007)."""
    if not sources:
        return DataMode.MOCK.value
    modes = {s.data_mode for s in sources}
    if len(modes) == 1:
        return modes.pop()
    return "mixed"


def _variants_and_offers_for_market(
    db: Session, product_id: uuid.UUID, market_code: str
) -> list[Offer]:
    variants = db.query(ProductVariant).filter_by(product_id=product_id).all()
    offers: list[Offer] = []
    for v in variants:
        market = db.get(Market, v.market_id)
        if market and market.code == market_code:
            offers.extend(db.query(Offer).filter_by(product_variant_id=v.id).all())
    return offers


@router.get("", response_model=OpportunityListResponse)
def list_opportunities(
    response: Response,
    db: Session = Depends(get_db),
    min_score: float = Query(0, ge=0, le=100),
    min_confidence: float = Query(0, ge=0, le=100),
    max_kr_sellers: int | None = Query(None, ge=0),
    status: str | None = None,
    sort_by: str = Query(
        "opportunity_score", pattern="^(opportunity_score|confidence_score|created_at)$"
    ),
    order: str = Query("desc", pattern="^(asc|desc)$"),
) -> OpportunityListResponse:
    q = db.query(Opportunity)
    if status:
        try:
            status_enum = OpportunityStatus(status)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"invalid status: {status}") from e
        q = q.filter(Opportunity.status == status_enum)
    else:
        # Superseded recomputes (docs/EVALUATION.md §6) stay in the table for
        # history but must not clutter the default "what's current" view —
        # pass ?status=STALE explicitly to see them.
        q = q.filter(Opportunity.status != OpportunityStatus.STALE)
    opportunities = q.all()

    items = []
    for opp in opportunities:
        if float(opp.opportunity_score) < min_score or float(opp.confidence_score) < min_confidence:
            continue
        kr_seller_count = opp.economics.get("kr_seller_count", 0)
        if max_kr_sellers is not None and kr_seller_count > max_kr_sellers:
            continue
        product = db.get(Product, opp.product_id)
        source = db.query(Source).filter_by(is_mock=True).first()
        items.append(
            OpportunityListItem(
                id=opp.id,
                product_id=opp.product_id,
                product_title=product.canonical_title if product else "",
                opportunity_score=float(opp.opportunity_score),
                confidence_score=float(opp.confidence_score),
                market_pair="JP -> KR",
                japan_purchase_price_jpy=opp.economics["japan_purchase_price_jpy"],
                korea_sale_price_krw=opp.economics["target_sale_price_krw"],
                expected_margin_krw=opp.economics["contribution_margin_krw"],
                kr_seller_count=kr_seller_count,
                status=opp.status.value,
                is_mock=source.is_mock if source else True,
                data_mode=source.data_mode.value if source else DataMode.MOCK.value,
                created_at=opp.created_at,
            )
        )

    reverse = order == "desc"
    items.sort(key=lambda i: getattr(i, sort_by), reverse=reverse)

    data_mode = system_data_mode(db)
    response.headers["X-Omnis-Data-Mode"] = data_mode
    return OpportunityListResponse(items=items, total=len(items), data_mode=data_mode)


@router.get("/{opportunity_id}", response_model=OpportunityDetail)
def get_opportunity(opportunity_id: uuid.UUID, db: Session = Depends(get_db)) -> OpportunityDetail:
    opp = db.get(Opportunity, opportunity_id)
    if opp is None:
        raise HTTPException(status_code=404, detail="opportunity not found")
    product = db.get(Product, opp.product_id)

    jp_offers = _variants_and_offers_for_market(db, opp.product_id, "JP")
    kr_offers = _variants_and_offers_for_market(db, opp.product_id, "KR")

    def _offer_summary(offer: Offer) -> dict:
        variant = db.get(ProductVariant, offer.product_variant_id)
        seller = db.get(Seller, offer.seller_id) if offer.seller_id else None
        latest = facts.latest_price(db, offer.id)
        inv = facts.latest_inventory(db, offer.id)
        return {
            "offer_id": str(offer.id),
            "listing_url": offer.listing_url,
            "seller_name": seller.name if seller else None,
            "title_raw": variant.title_raw if variant else None,
            "latest_price": latest.price_amount if latest else None,
            "currency_code": offer.currency_code,
            "in_stock": inv.in_stock if inv else None,
        }

    price_history_jp = [
        PriceHistoryPoint(
            observed_at=p.observed_at,
            price_amount=p.price_amount,
            currency_code=p.currency_code,
            source_snapshot_id=p.source_snapshot_id,
        )
        for o in jp_offers
        for p in facts.price_history(db, o.id)
    ]
    price_history_kr = [
        PriceHistoryPoint(
            observed_at=p.observed_at,
            price_amount=p.price_amount,
            currency_code=p.currency_code,
            source_snapshot_id=p.source_snapshot_id,
        )
        for o in kr_offers
        for p in facts.price_history(db, o.id)
    ]

    # Only matches that actually contributed to merging this product — not
    # every comparison its variants were ever part of (which would include
    # a long tail of unrelated REJECTED pairs against other products and
    # bury the evidence that actually matters here).
    matches = db.query(EntityMatch).filter_by(resolved_product_id=opp.product_id).all()
    entity_matches = []
    for m in matches:
        left = db.get(ProductVariant, m.left_variant_id)
        right = db.get(ProductVariant, m.right_variant_id)
        entity_matches.append(
            EntityMatchEvidenceItem(
                id=m.id,
                left_variant_id=m.left_variant_id,
                right_variant_id=m.right_variant_id,
                left_title=left.title_raw if left else "",
                right_title=right.title_raw if right else "",
                match_type=m.match_type.value,
                match_stage=m.match_stage.value,
                match_confidence=float(m.match_confidence),
                evidence=m.evidence,
                algorithm_version=m.algorithm_version,
            )
        )

    offer_ids = {o.id for o in jp_offers + kr_offers}
    event_rows = (
        db.query(Event)
        .filter(Event.entity_type == EventEntityType.OFFER, Event.entity_id.in_(offer_ids))
        .all()
    )
    event_rows += (
        db.query(Event)
        .filter(Event.entity_type == EventEntityType.PRODUCT, Event.entity_id == opp.product_id)
        .all()
    )
    events = [
        EventItem(
            id=e.id,
            event_type=e.event_type.value,
            previous_value=e.previous_value,
            new_value=e.new_value,
            change_pct=float(e.change_pct) if e.change_pct is not None else None,
            observed_at=e.observed_at,
            confidence=float(e.confidence),
        )
        for e in event_rows
    ]

    insight_rows = db.query(Insight).filter_by(product_id=opp.product_id).all()
    insights = [
        InsightItem(
            id=i.id,
            kind=i.kind.value,
            title=i.title,
            narrative=i.narrative,
            is_ai_generated=i.is_ai_generated,
            confidence=float(i.confidence),
        )
        for i in insight_rows
    ]

    source_ids = (
        {p.source_id for p in facts.price_history(db, jp_offers[0].id)} if jp_offers else set()
    )
    for o in kr_offers[:1]:
        source_ids |= {p.source_id for p in facts.price_history(db, o.id)}
    sources = [
        SourceRef.model_validate(db.get(Source, sid)) for sid in source_ids if db.get(Source, sid)
    ]

    decisions = db.query(UserDecision).filter_by(opportunity_id=opp.id).all()

    latest_forecast_row = (
        db.query(Forecast)
        .filter_by(product_id=opp.product_id)
        .order_by(Forecast.forecast_created_at.desc())
        .first()
    )
    latest_forecast = (
        ForecastItem(
            id=latest_forecast_row.id,
            predicted_direction=latest_forecast_row.predicted_direction.value,
            predicted_probability=latest_forecast_row.predicted_probability,
            confidence_tier=latest_forecast_row.confidence_tier.value,
            is_calibrated=latest_forecast_row.is_calibrated,
            forecast_horizon_days=latest_forecast_row.forecast_horizon_days,
            evidence=latest_forecast_row.evidence,
            created_at=latest_forecast_row.forecast_created_at,
        )
        if latest_forecast_row
        else None
    )

    return OpportunityDetail(
        id=opp.id,
        product_id=opp.product_id,
        product_title=product.canonical_title if product else "",
        opportunity_type=opp.opportunity_type.value,
        opportunity_score=float(opp.opportunity_score),
        confidence_score=float(opp.confidence_score),
        sub_scores=opp.sub_scores,
        weights_version=opp.weights_version,
        economics=opp.economics,
        regulation_status=opp.regulation_status.value,
        regulation_basis=opp.regulation_basis,
        status=opp.status.value,
        created_at=opp.created_at,
        analysis_run_id=opp.analysis_run_id,
        japan_offers=[_offer_summary(o) for o in jp_offers],
        korea_offers=[_offer_summary(o) for o in kr_offers],
        price_history_jp=sorted(price_history_jp, key=lambda p: p.observed_at),
        price_history_kr=sorted(price_history_kr, key=lambda p: p.observed_at),
        entity_matches=entity_matches,
        events=events,
        insights=insights,
        sources=sources,
        decisions=[
            UserDecisionItem(
                id=d.id,
                decision=d.decision.value,
                reason=d.reason,
                note=d.note,
                created_at=d.created_at,
            )
            for d in decisions
        ],
        is_mock=all(s.is_mock for s in sources) if sources else True,
        data_mode=_opportunity_data_mode(sources),
        latest_forecast=latest_forecast,
    )


def _history_point(opp: Opportunity) -> OpportunityHistoryPoint:
    econ = opp.economics
    return OpportunityHistoryPoint(
        opportunity_id=opp.id,
        analysis_run_id=opp.analysis_run_id,
        status=opp.status.value,
        opportunity_score=float(opp.opportunity_score),
        confidence_score=float(opp.confidence_score),
        contribution_margin_krw=econ.get("contribution_margin_krw"),
        jpy_krw_fx=econ.get("jpy_krw_fx"),
        japan_purchase_price_jpy=econ.get("japan_purchase_price_jpy"),
        korea_sale_price_krw=econ.get("target_sale_price_krw"),
        created_at=opp.created_at,
    )


@router.get("/{opportunity_id}/history", response_model=OpportunityHistoryResponse)
def get_opportunity_history(
    opportunity_id: uuid.UUID,
    as_of: datetime | None = Query(
        None, description="Reconstruct which opportunity state was current at or before this time."
    ),
    db: Session = Depends(get_db),
) -> OpportunityHistoryResponse:
    """docs/MASTER_SPEC.md §6: every recompute keeps its own row (superseded
    ones marked STALE, never deleted or overwritten — docs/EVALUATION.md §6),
    so the full opportunity_score/confidence/margin/FX time series for a
    product, and its state as of any past moment, is a query over that
    existing history rather than a separate table."""
    opp = db.get(Opportunity, opportunity_id)
    if opp is None:
        raise HTTPException(status_code=404, detail="opportunity not found")

    rows = (
        db.query(Opportunity)
        .filter_by(product_id=opp.product_id)
        .order_by(Opportunity.created_at.asc())
        .all()
    )
    points = [_history_point(o) for o in rows]

    current = None
    if as_of is not None:
        points = [p for p in points if p.created_at <= as_of]
        current = points[-1] if points else None

    return OpportunityHistoryResponse(
        product_id=opp.product_id, as_of=as_of, points=points, current=current
    )


@router.post("/{opportunity_id}/decisions", response_model=UserDecisionItem, status_code=201)
def create_decision(
    opportunity_id: uuid.UUID, payload: UserDecisionCreate, db: Session = Depends(get_db)
) -> UserDecisionItem:
    opp = db.get(Opportunity, opportunity_id)
    if opp is None:
        raise HTTPException(status_code=404, detail="opportunity not found")
    try:
        decision_enum = DecisionType(payload.decision)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"invalid decision: {payload.decision}") from e
    decision = UserDecision(
        opportunity_id=opportunity_id,
        user_email=payload.user_email,
        decision=decision_enum,
        reason=payload.reason,
        note=payload.note,
    )
    db.add(decision)
    db.commit()
    db.refresh(decision)
    return UserDecisionItem(
        id=decision.id,
        decision=decision.decision.value,
        reason=decision.reason,
        note=decision.note,
        created_at=decision.created_at,
    )


@router.get("/{opportunity_id}/decisions", response_model=list[UserDecisionItem])
def list_decisions(
    opportunity_id: uuid.UUID, db: Session = Depends(get_db)
) -> list[UserDecisionItem]:
    decisions = db.query(UserDecision).filter_by(opportunity_id=opportunity_id).all()
    return [
        UserDecisionItem(
            id=d.id,
            decision=d.decision.value,
            reason=d.reason,
            note=d.note,
            created_at=d.created_at,
        )
        for d in decisions
    ]
