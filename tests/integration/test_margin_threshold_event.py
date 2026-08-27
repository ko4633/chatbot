"""MARGIN_THRESHOLD_CROSSED: the one deterministic profitability threshold
that needs no tunable config (margin rate crossing zero), independent of
whether the opportunity score also moved enough to fire
OPPORTUNITY_SCORE_CHANGE. See packages/intelligence/opportunity_builder.py
and product brief §6.
"""

from __future__ import annotations

from packages.ai.null_provider import NullAIProvider
from packages.collectors.japan_marketplace import JapanMarketplaceProvider
from packages.collectors.korea_marketplace import KoreaMarketplaceProvider
from packages.collectors.storage import LocalFileStore
from packages.db.enums import EventType
from packages.db.models.event import Event
from packages.db.models.observations import PriceObservation
from packages.db.models.offer import Offer
from packages.db.models.product import Product, ProductVariant
from packages.db.models.opportunity import Opportunity
from packages.intelligence.opportunity_builder import build_opportunities
from packages.intelligence.pipeline import run_full_analysis


def test_margin_sign_flip_fires_margin_threshold_crossed_event(clean_db, tmp_path):
    store = LocalFileStore(str(tmp_path / "raw"))
    run1 = run_full_analysis(
        clean_db,
        NullAIProvider(),
        [JapanMarketplaceProvider(), KoreaMarketplaceProvider()],
        store,
        triggered_by="pytest",
    )

    opportunities = {
        clean_db.get(Product, o.product_id).canonical_title: o
        for o in clean_db.query(Opportunity).all()
    }
    thermos_450 = next(o for t, o in opportunities.items() if "JNL-450" in t)
    assert float(thermos_450.economics["contribution_margin_krw"]) > 0  # sanity, per existing test

    # Flip its JP purchase price way up so the same KR sale price now yields
    # a negative contribution margin — a genuine profitability threshold
    # crossing, not a score-magnitude coincidence.
    variants = clean_db.query(ProductVariant).filter_by(product_id=thermos_450.product_id).all()
    jp_offer_ids = [
        o.id
        for v in variants
        for o in clean_db.query(Offer).filter_by(product_variant_id=v.id).all()
        if o.currency_code == "JPY"
    ]
    price_obs = (
        clean_db.query(PriceObservation).filter(PriceObservation.offer_id.in_(jp_offer_ids)).all()
    )
    for p in price_obs:
        p.price_amount = 500_000  # absurdly high JPY price forces negative margin
    clean_db.commit()

    stats = build_opportunities(clean_db, run1.id)
    clean_db.commit()
    assert stats.opportunities_created > 0

    events = (
        clean_db.query(Event)
        .filter_by(entity_id=thermos_450.product_id, event_type=EventType.MARGIN_THRESHOLD_CROSSED)
        .all()
    )
    assert len(events) == 1
    assert events[0].previous_value["contribution_margin_krw"] > 0
    assert events[0].new_value["contribution_margin_krw"] < 0


def test_margin_threshold_event_does_not_fire_when_margin_stays_same_sign(clean_db, tmp_path):
    store = LocalFileStore(str(tmp_path / "raw"))
    run1 = run_full_analysis(
        clean_db,
        NullAIProvider(),
        [JapanMarketplaceProvider(), KoreaMarketplaceProvider()],
        store,
        triggered_by="pytest",
    )
    build_opportunities(clean_db, run1.id)
    clean_db.commit()

    events = clean_db.query(Event).filter_by(event_type=EventType.MARGIN_THRESHOLD_CROSSED).all()
    assert events == []
