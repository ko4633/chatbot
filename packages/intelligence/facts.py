""" "Fact" as a query over Observations, never a materialized table — see
ADR-0004. packages/scoring and packages/intelligence consume these
functions exclusively; nothing queries the Observation tables directly for
"current value" outside this module.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy.orm import Session

from packages.core.time_utils import utcnow
from packages.db.models.fx import FXObservation
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


def fx_history(db: Session, base_currency: str, quote_currency: str) -> list[FXObservation]:
    return (
        db.query(FXObservation)
        .filter_by(base_currency=base_currency.upper(), quote_currency=quote_currency.upper())
        .order_by(FXObservation.observed_at.asc())
        .all()
    )


def latest_fx(db: Session, base_currency: str, quote_currency: str) -> FXObservation | None:
    return (
        db.query(FXObservation)
        .filter_by(base_currency=base_currency.upper(), quote_currency=quote_currency.upper())
        .order_by(FXObservation.observed_at.desc())
        .first()
    )


def fx_as_of(db: Session, base_currency: str, quote_currency: str, as_of: date) -> FXObservation | None:
    """Answers "환율은 상품 발견 당시 얼마였는가" (product brief §6) — the
    most recent FX observation at or before the given date."""
    return (
        db.query(FXObservation)
        .filter(
            FXObservation.base_currency == base_currency.upper(),
            FXObservation.quote_currency == quote_currency.upper(),
            FXObservation.observed_at <= datetime.combine(as_of, datetime.max.time()),
        )
        .order_by(FXObservation.observed_at.desc())
        .first()
    )


def is_fx_stale(observation: FXObservation | None, stale_after_hours: int) -> bool:
    """See docs/DATA_MODEL.md FX freshness / product brief §9. A missing
    observation counts as stale (never treated as "fine") — the caller
    already has to handle None separately for the "no FX data at all" case."""
    if observation is None:
        return True
    age_hours = (utcnow() - observation.observed_at).total_seconds() / 3600
    return age_hours > stale_after_hours
