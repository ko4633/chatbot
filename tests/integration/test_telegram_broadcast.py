"""Telegram broadcast, exercised against the bundled JP/KR demo fixtures
(same pipeline the other integration tests use) with a fake adapter — no
real network call, so this proves the wiring/filtering logic without
depending on api.telegram.org (docs/ADR/0010).
"""

from __future__ import annotations

from packages.ai.null_provider import NullAIProvider
from packages.collectors.japan_marketplace import JapanMarketplaceProvider
from packages.collectors.korea_marketplace import KoreaMarketplaceProvider
from packages.collectors.storage import LocalFileStore
from packages.db.models.opportunity import Opportunity
from packages.intelligence.pipeline import run_full_analysis
from packages.telegram.adapter import TelegramAdapter
from packages.telegram.broadcast import broadcast_new_opportunities
from packages.telegram.types import TelegramSendResult


class FakeTelegramAdapter(TelegramAdapter):
    def __init__(self, fail: bool = False) -> None:
        self.sent_messages: list[tuple[str, str]] = []
        self._fail = fail

    def send_message(self, chat_id: str, text: str) -> TelegramSendResult:
        if self._fail:
            return TelegramSendResult(sent=False, chat_id=chat_id, message_id=None, error="fake failure")
        self.sent_messages.append((chat_id, text))
        return TelegramSendResult(sent=True, chat_id=chat_id, message_id=len(self.sent_messages))

    def get_updates(self, offset=None, timeout_seconds=30):
        return []


def _run_pipeline(db, tmp_path):
    store = LocalFileStore(str(tmp_path / "raw"))
    return run_full_analysis(
        db,
        NullAIProvider(),
        [JapanMarketplaceProvider(), KoreaMarketplaceProvider()],
        store,
        triggered_by="pytest",
    )


def test_broadcast_sends_one_message_per_new_opportunity_above_threshold(clean_db, tmp_path):
    run = _run_pipeline(clean_db, tmp_path)
    opportunities = clean_db.query(Opportunity).filter_by(analysis_run_id=run.id).all()
    assert len(opportunities) == 4

    adapter = FakeTelegramAdapter()
    stats = broadcast_new_opportunities(clean_db, adapter, run.id, chat_id="123", min_score=0.0)

    assert stats.opportunities_considered == 4
    assert stats.messages_sent == 4
    assert stats.messages_failed == 0
    assert len(adapter.sent_messages) == 4
    for chat_id, text in adapter.sent_messages:
        assert chat_id == "123"
        assert "New Opportunity" in text


def test_broadcast_respects_min_score_threshold(clean_db, tmp_path):
    run = _run_pipeline(clean_db, tmp_path)
    opportunities = clean_db.query(Opportunity).filter_by(analysis_run_id=run.id).all()
    high_threshold = max(float(o.opportunity_score) for o in opportunities) + 1

    adapter = FakeTelegramAdapter()
    stats = broadcast_new_opportunities(
        clean_db, adapter, run.id, chat_id="123", min_score=high_threshold
    )
    assert stats.opportunities_considered == 0
    assert stats.messages_sent == 0


def test_broadcast_counts_adapter_failures_without_raising(clean_db, tmp_path):
    run = _run_pipeline(clean_db, tmp_path)
    adapter = FakeTelegramAdapter(fail=True)
    stats = broadcast_new_opportunities(clean_db, adapter, run.id, chat_id="123", min_score=0.0)
    assert stats.messages_failed == stats.opportunities_considered
    assert stats.messages_sent == 0


def test_rerun_does_not_rebroadcast_stale_opportunities(clean_db, tmp_path):
    run1 = _run_pipeline(clean_db, tmp_path)
    run2 = _run_pipeline(clean_db, tmp_path)

    adapter = FakeTelegramAdapter()
    # run1's opportunities are now STALE (superseded by run2) — broadcasting
    # for run1's id again must not resend them.
    stats = broadcast_new_opportunities(clean_db, adapter, run1.id, chat_id="123", min_score=0.0)
    assert stats.opportunities_considered == 0
