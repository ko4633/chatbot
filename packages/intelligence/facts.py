""" "Fact" as a query over Observations, never a materialized table — see
ADR-0004. packages/scoring and packages/intelligence consume these
functions exclusively; nothing queries the Observation tables directly for
"current value" outside this module.
"""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from packages.db.models.observations import (
    InventoryObservation,
    PriceObservation,
    ReviewObservation,
)


def price_history(db: Session, offer_id: uuid.UUID) -> list[PriceObservation]:
    return (
        db.query(PriceObservation)
        .filter_by(offer_id=offer_id)
        .order_by(PriceObservation.observed_at.asc())
        .all()
    )


def latest_price(db: Session, offer_id: uuid.UUID) -> PriceObservation | None:
    return (
        db.query(PriceObservation)
        .filter_by(offer_id=offer_id)
        .order_by(PriceObservation.observed_at.desc())
        .first()
    )


def oldest_price(db: Session, offer_id: uuid.UUID) -> PriceObservation | None:
    return (
        db.query(PriceObservation)
        .filter_by(offer_id=offer_id)
        .order_by(PriceObservation.observed_at.asc())
        .first()
    )


def latest_inventory(db: Session, offer_id: uuid.UUID) -> InventoryObservation | None:
    return (
        db.query(InventoryObservation)
        .filter_by(offer_id=offer_id)
        .order_by(InventoryObservation.observed_at.desc())
        .first()
    )


def latest_review_stats(db: Session, product_variant_id: uuid.UUID) -> ReviewObservation | None:
    return (
        db.query(ReviewObservation)
        .filter_by(product_variant_id=product_variant_id)
        .order_by(ReviewObservation.observed_at.desc())
        .first()
    )
