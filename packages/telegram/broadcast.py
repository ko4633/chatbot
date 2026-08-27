"""Pushes newly-created high-value Opportunities to the configured Telegram
channel (product brief §15A). No scoring/filtering logic beyond a plain
score threshold lives here — the Opportunity was already fully scored by
packages/scoring before this module ever sees it (docs/ADR/0010).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy.orm import Session

from packages.db.enums import InsightKind, OpportunityStatus
from packages.db.models.insight import Insight
from packages.db.models.opportunity import Opportunity
from packages.db.models.product import Product
from packages.intelligence.system_status import system_data_mode
from packages.observability.logging import get_logger
from packages.telegram.adapter import TelegramAdapter
from packages.telegram.formatter import format_opportunity_broadcast

logger = get_logger(__name__)


@dataclass
class BroadcastStats:
    opportunities_considered: int = 0
    messages_sent: int = 0
    messages_failed: int = 0


def _latest_insight(db: Session, product_id: uuid.UUID, kind: InsightKind) -> Insight | None:
    return (
        db.query(Insight)
        .filter_by(product_id=product_id, kind=kind)
        .order_by(Insight.created_at.desc())
        .first()
    )


def broadcast_new_opportunities(
    db: Session,
    adapter: TelegramAdapter,
    analysis_run_id: uuid.UUID,
    chat_id: str,
    min_score: float = 70.0,
) -> BroadcastStats:
    """Only Opportunity.status == NEW (the first time this product cleared
    the cross-market match), never a STALE-superseded row or a routine
    recompute — a re-run of the same opportunity fires an
    OPPORTUNITY_SCORE_CHANGE/FX_DRIVEN_OPPORTUNITY Event instead, which is a
    separate, not-yet-wired broadcast trigger (see BUILD STATUS report)."""
    stats = BroadcastStats()
    data_mode = system_data_mode(db)
    opportunities = (
        db.query(Opportunity)
        .filter(
            Opportunity.analysis_run_id == analysis_run_id,
            Opportunity.status == OpportunityStatus.NEW,
            Opportunity.opportunity_score >= min_score,
        )
        .all()
    )
    for opp in opportunities:
        stats.opportunities_considered += 1
        product = db.get(Product, opp.product_id)
        why_now = _latest_insight(db, opp.product_id, InsightKind.WHY_NOW)
        counter_argument = _latest_insight(db, opp.product_id, InsightKind.COUNTER_ARGUMENT)
        text = format_opportunity_broadcast(
            opp,
            product.canonical_title if product else "Unknown product",
            data_mode,
            why_now_narrative=why_now.narrative if why_now else None,
            counter_argument_narrative=counter_argument.narrative if counter_argument else None,
        )
        result = adapter.send_message(chat_id, text)
        if result.sent:
            stats.messages_sent += 1
        else:
            stats.messages_failed += 1
            logger.warning(
                "telegram_broadcast_failed", opportunity_id=str(opp.id), error=result.error
            )
    return stats
