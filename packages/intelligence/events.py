"""Event detection: compares consecutive Observations, never invents a
change that isn't directly backed by two real observation rows. See
docs/DATA_MODEL.md `event` and docs/ARCHITECTURE.md §2.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy.orm import Session

from packages.db.enums import EventEntityType, EventType
from packages.db.models.event import Event
from packages.db.models.offer import Offer
from packages.intelligence import facts

PRICE_CHANGE_THRESHOLD_PCT = 0.03  # below this, treated as noise, not a PRICE_DROP/RISE event


@dataclass
class EventDetectionStats:
    events_created: int = 0


def _event_already_recorded(
    db: Session, entity_id: uuid.UUID, event_type: EventType, observed_at
) -> bool:
    return (
        db.query(Event)
        .filter_by(entity_id=entity_id, event_type=event_type, observed_at=observed_at)
        .first()
        is not None
    )


def detect_price_events(db: Session, analysis_run_id: uuid.UUID) -> EventDetectionStats:
    stats = EventDetectionStats()
    for offer in db.query(Offer).all():
        history = facts.price_history(db, offer.id)
        if len(history) < 2:
            continue
        previous, latest = history[-2], history[-1]
        if previous.price_amount <= 0:
            continue
        change_pct = (latest.price_amount - previous.price_amount) / previous.price_amount
        if abs(change_pct) < PRICE_CHANGE_THRESHOLD_PCT:
            continue
        event_type = EventType.PRICE_DROP if change_pct < 0 else EventType.PRICE_RISE
        if _event_already_recorded(db, offer.id, event_type, latest.observed_at):
            continue
        db.add(
            Event(
                entity_type=EventEntityType.OFFER,
                entity_id=offer.id,
                event_type=event_type,
                previous_value={
                    "price_amount": previous.price_amount,
                    "currency_code": previous.currency_code,
                },
                new_value={
                    "price_amount": latest.price_amount,
                    "currency_code": latest.currency_code,
                },
                change_pct=round(change_pct * 100, 2),
                observed_at=latest.observed_at,
                evidence={
                    "previous_observation_id": str(previous.id),
                    "new_observation_id": str(latest.id),
                },
                confidence=1.0,  # directly computed from two real observations — not a guess
                analysis_run_id=analysis_run_id,
            )
        )
        db.flush()
        stats.events_created += 1
    return stats
