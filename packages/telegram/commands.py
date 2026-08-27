"""Personal-bot query commands (product brief §15B). Every handler queries
the same tables/fields apps/api's routers query, with the same filter/sort
semantics — this file must never grow its own competing notion of "top" or
"filtered" (docs/ADR/0010): if the bot and the website ever disagreed about
which opportunities are "top 10 today," that disagreement would itself be
the bug this boundary exists to prevent.

WatchlistItem.user_email (packages/db/models/decision.py) is reused as a
generic "who is tracking this" identifier here, holding a Telegram chat id
instead of an email — a real second identity column would be schema
overhead for a distinction (email vs chat id) nothing currently queries on.
"""

from __future__ import annotations

import uuid
from datetime import timedelta

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from packages.core.time_utils import utcnow
from packages.db.enums import EventEntityType, InsightKind, OpportunityStatus, WatchlistEntityType
from packages.db.models.decision import WatchlistItem
from packages.db.models.event import Event
from packages.db.models.insight import Insight
from packages.db.models.offer import Offer
from packages.db.models.opportunity import Opportunity
from packages.db.models.product import Product, ProductVariant


def top_opportunities(db: Session, limit: int = 10) -> str:
    opportunities = (
        db.query(Opportunity)
        .filter(Opportunity.status != OpportunityStatus.STALE)
        .order_by(Opportunity.opportunity_score.desc())
        .limit(limit)
        .all()
    )
    if not opportunities:
        return "No active opportunities right now."
    lines = [f"Top {len(opportunities)} opportunities:"]
    for i, opp in enumerate(opportunities, start=1):
        product = db.get(Product, opp.product_id)
        lines.append(
            f"{i}. {product.canonical_title if product else 'Unknown'} "
            f"(id={opp.id}) — score {opp.opportunity_score}, confidence {opp.confidence_score}"
        )
    return "\n".join(lines)


def filter_opportunities(
    db: Session,
    min_score: float = 0.0,
    min_margin_krw: float | None = None,
    max_kr_sellers: int | None = None,
) -> str:
    opportunities = (
        db.query(Opportunity)
        .filter(
            Opportunity.status != OpportunityStatus.STALE,
            Opportunity.opportunity_score >= min_score,
        )
        .all()
    )
    if min_margin_krw is not None:
        opportunities = [
            o for o in opportunities if o.economics.get("contribution_margin_krw", 0) >= min_margin_krw
        ]
    if max_kr_sellers is not None:
        opportunities = [
            o for o in opportunities if o.economics.get("kr_seller_count", 0) <= max_kr_sellers
        ]
    if not opportunities:
        return "No opportunities match those filters."
    lines = [f"{len(opportunities)} opportunit{'y' if len(opportunities) == 1 else 'ies'} match:"]
    for opp in opportunities:
        product = db.get(Product, opp.product_id)
        lines.append(
            f"- {product.canonical_title if product else 'Unknown'} (id={opp.id}) — "
            f"score {opp.opportunity_score}, margin {opp.economics.get('contribution_margin_krw')} KRW, "
            f"{opp.economics.get('kr_seller_count')} KR seller(s)"
        )
    return "\n".join(lines)


def _latest_insight_narrative(db: Session, product_id: uuid.UUID, kind: InsightKind) -> str | None:
    insight = (
        db.query(Insight)
        .filter_by(product_id=product_id, kind=kind)
        .order_by(Insight.created_at.desc())
        .first()
    )
    return insight.narrative if insight else None


def why_recommended(db: Session, opportunity_id: uuid.UUID) -> str:
    opp = db.get(Opportunity, opportunity_id)
    if opp is None:
        return "Opportunity not found."
    narrative = _latest_insight_narrative(db, opp.product_id, InsightKind.WHY_NOW)
    return narrative or "No Why Now insight recorded yet for this opportunity."


def counter_argument(db: Session, opportunity_id: uuid.UUID) -> str:
    opp = db.get(Opportunity, opportunity_id)
    if opp is None:
        return "Opportunity not found."
    narrative = _latest_insight_narrative(db, opp.product_id, InsightKind.COUNTER_ARGUMENT)
    return narrative or "No counter-argument recorded yet for this opportunity."


def track_product(db: Session, chat_id: str, product_id: uuid.UUID) -> str:
    product = db.get(Product, product_id)
    if product is None:
        return "Product not found."
    existing = (
        db.query(WatchlistItem)
        .filter_by(
            user_email=chat_id,
            entity_type=WatchlistEntityType.PRODUCT,
            entity_ref=str(product_id),
        )
        .first()
    )
    if existing:
        return f"Already tracking {product.canonical_title}."
    db.add(
        WatchlistItem(
            user_email=chat_id,
            entity_type=WatchlistEntityType.PRODUCT,
            entity_ref=str(product_id),
            note="added via Telegram bot",
        )
    )
    db.commit()
    return f"Now tracking {product.canonical_title}."


def changes_last_n_days(db: Session, product_id: uuid.UUID, days: int = 30) -> str:
    product = db.get(Product, product_id)
    if product is None:
        return "Product not found."
    since = utcnow() - timedelta(days=days)
    variants = db.query(ProductVariant).filter_by(product_id=product_id).all()
    offer_ids = {
        o.id for v in variants for o in db.query(Offer).filter_by(product_variant_id=v.id).all()
    }
    conditions = [and_(Event.entity_type == EventEntityType.PRODUCT, Event.entity_id == product_id)]
    if offer_ids:
        conditions.append(
            and_(Event.entity_type == EventEntityType.OFFER, Event.entity_id.in_(offer_ids))
        )
    events = (
        db.query(Event)
        .filter(Event.observed_at >= since, or_(*conditions))
        .order_by(Event.observed_at.desc())
        .all()
    )
    if not events:
        return f"No changes recorded for {product.canonical_title} in the last {days} days."
    lines = [f"Changes for {product.canonical_title} in the last {days} days:"]
    for e in events:
        pct = f" ({e.change_pct}%)" if e.change_pct is not None else ""
        lines.append(f"- {e.event_type.value}{pct} at {e.observed_at.isoformat()}")
    return "\n".join(lines)


HELP_TEXT = (
    "Commands:\n"
    "/top [n] - top N opportunities by score (default 10)\n"
    "/filter min_score=<n> [min_margin=<n>] [max_sellers=<n>] - filtered list\n"
    "/why <opportunity_id> - why this was recommended\n"
    "/counter <opportunity_id> - counter-argument / risks\n"
    "/track <product_id> - track a product\n"
    "/changes <product_id> [days] - recent changes (default 30 days)"
)


def _parse_filter_args(args: list[str]) -> dict:
    parsed: dict = {}
    for arg in args:
        if "=" not in arg:
            continue
        key, _, value = arg.partition("=")
        if key == "min_score":
            parsed["min_score"] = float(value)
        elif key == "min_margin":
            parsed["min_margin_krw"] = float(value)
        elif key == "max_sellers":
            parsed["max_kr_sellers"] = int(value)
    return parsed


def dispatch_command(db: Session, chat_id: str, text: str) -> str:
    """The one entry point both the live polling loop and tests use — never
    call the individual handlers directly from outside this module except
    in tests, so command parsing has exactly one code path."""
    parts = text.strip().split()
    if not parts:
        return HELP_TEXT
    cmd = parts[0].lower().lstrip("/")
    args = parts[1:]
    try:
        if cmd == "top":
            limit = int(args[0]) if args else 10
            return top_opportunities(db, limit=limit)
        if cmd == "filter":
            return filter_opportunities(db, **_parse_filter_args(args))
        if cmd == "why":
            return why_recommended(db, uuid.UUID(args[0]))
        if cmd == "counter":
            return counter_argument(db, uuid.UUID(args[0]))
        if cmd == "track":
            return track_product(db, chat_id, uuid.UUID(args[0]))
        if cmd == "changes":
            days = int(args[1]) if len(args) > 1 else 30
            return changes_last_n_days(db, uuid.UUID(args[0]), days=days)
        if cmd in ("help", "start"):
            return HELP_TEXT
    except (ValueError, IndexError):
        return "Sorry, I couldn't parse that command. Send /help for usage."
    return "Unknown command. Send /help for usage."
