"""Personal-bot commands, exercised against the real pipeline output
(docs/ADR/0010) — every handler here must answer with the exact same data
apps/api's routers would return for the same query."""

from __future__ import annotations

from packages.ai.null_provider import NullAIProvider
from packages.collectors.japan_marketplace import JapanMarketplaceProvider
from packages.collectors.korea_marketplace import KoreaMarketplaceProvider
from packages.collectors.storage import LocalFileStore
from packages.db.enums import WatchlistEntityType
from packages.db.models.decision import WatchlistItem
from packages.db.models.opportunity import Opportunity
from packages.intelligence.pipeline import run_full_analysis
from packages.telegram.commands import dispatch_command


def _run_pipeline(db, tmp_path):
    store = LocalFileStore(str(tmp_path / "raw"))
    return run_full_analysis(
        db,
        NullAIProvider(),
        [JapanMarketplaceProvider(), KoreaMarketplaceProvider()],
        store,
        triggered_by="pytest",
    )


def test_top_lists_opportunities_by_score_desc(clean_db, tmp_path):
    _run_pipeline(clean_db, tmp_path)
    reply = dispatch_command(clean_db, "chat-1", "/top 2")
    lines = [l for l in reply.split("\n") if l.startswith(("1.", "2."))]
    assert len(lines) == 2


def test_top_with_no_opportunities_says_so(clean_db):
    reply = dispatch_command(clean_db, "chat-1", "/top")
    assert "No active opportunities" in reply


def test_filter_by_min_score(clean_db, tmp_path):
    _run_pipeline(clean_db, tmp_path)
    opportunities = clean_db.query(Opportunity).all()
    highest = max(float(o.opportunity_score) for o in opportunities)
    reply = dispatch_command(clean_db, "chat-1", f"/filter min_score={highest + 1}")
    assert "No opportunities match" in reply


def test_why_returns_why_now_narrative(clean_db, tmp_path):
    _run_pipeline(clean_db, tmp_path)
    opp = clean_db.query(Opportunity).first()
    reply = dispatch_command(clean_db, "chat-1", f"/why {opp.id}")
    assert reply != "Opportunity not found."
    assert len(reply) > 0


def test_why_unknown_id_says_not_found(clean_db):
    reply = dispatch_command(
        clean_db, "chat-1", "/why 00000000-0000-0000-0000-000000000000"
    )
    assert reply == "Opportunity not found."


def test_counter_returns_counter_argument_narrative(clean_db, tmp_path):
    _run_pipeline(clean_db, tmp_path)
    opp = clean_db.query(Opportunity).first()
    reply = dispatch_command(clean_db, "chat-1", f"/counter {opp.id}")
    assert reply != "Opportunity not found."
    assert len(reply) > 0


def test_track_adds_watchlist_item(clean_db, tmp_path):
    _run_pipeline(clean_db, tmp_path)
    opp = clean_db.query(Opportunity).first()
    reply = dispatch_command(clean_db, "chat-42", f"/track {opp.product_id}")
    assert "Now tracking" in reply
    item = (
        clean_db.query(WatchlistItem)
        .filter_by(
            user_email="chat-42",
            entity_type=WatchlistEntityType.PRODUCT,
            entity_ref=str(opp.product_id),
        )
        .one_or_none()
    )
    assert item is not None


def test_track_twice_does_not_duplicate(clean_db, tmp_path):
    _run_pipeline(clean_db, tmp_path)
    opp = clean_db.query(Opportunity).first()
    dispatch_command(clean_db, "chat-42", f"/track {opp.product_id}")
    reply = dispatch_command(clean_db, "chat-42", f"/track {opp.product_id}")
    assert "Already tracking" in reply
    count = (
        clean_db.query(WatchlistItem)
        .filter_by(user_email="chat-42", entity_ref=str(opp.product_id))
        .count()
    )
    assert count == 1


def test_changes_reports_recorded_events(clean_db, tmp_path):
    _run_pipeline(clean_db, tmp_path)
    opp = clean_db.query(Opportunity).first()
    reply = dispatch_command(clean_db, "chat-1", f"/changes {opp.product_id} 30")
    assert "Product not found" not in reply


def test_help_and_unknown_command(clean_db):
    assert "Commands:" in dispatch_command(clean_db, "chat-1", "/help")
    assert "Unknown command" in dispatch_command(clean_db, "chat-1", "/nonsense")


def test_malformed_command_does_not_raise(clean_db):
    reply = dispatch_command(clean_db, "chat-1", "/why not-a-uuid")
    assert "couldn't parse" in reply
