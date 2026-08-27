"""Polling loop dispatch (docs/ADR/0010) — a fake adapter feeds canned
Telegram getUpdates responses so this proves the offset/dispatch/reply wiring
without any real network call."""

from __future__ import annotations

from packages.core.settings import Settings
from packages.telegram.adapter import TelegramAdapter
from packages.telegram.bot_runner import run_polling_loop
from packages.telegram.types import TelegramSendResult


class ScriptedTelegramAdapter(TelegramAdapter):
    def __init__(self, batches: list[list[dict]]) -> None:
        self._batches = batches
        self._call_count = 0
        self.sent: list[tuple[str, str]] = []
        self.offsets_seen: list[int | None] = []

    def get_updates(self, offset=None, timeout_seconds=30):
        self.offsets_seen.append(offset)
        if self._call_count < len(self._batches):
            batch = self._batches[self._call_count]
        else:
            batch = []
        self._call_count += 1
        return batch

    def send_message(self, chat_id: str, text: str) -> TelegramSendResult:
        self.sent.append((chat_id, text))
        return TelegramSendResult(sent=True, chat_id=chat_id, message_id=len(self.sent))


def _settings() -> Settings:
    return Settings(telegram_bot_token="fake-token", telegram_chat_id="fake-chat")


def test_polling_loop_dispatches_command_and_replies(clean_db, monkeypatch):
    import packages.telegram.bot_runner as bot_runner_module

    monkeypatch.setattr(bot_runner_module, "get_session_factory", lambda: (lambda: clean_db))

    adapter = ScriptedTelegramAdapter(
        [[{"update_id": 100, "message": {"text": "/help", "chat": {"id": 999}}}]]
    )
    run_polling_loop(settings=_settings(), adapter=adapter, max_iterations=1)

    assert len(adapter.sent) == 1
    chat_id, reply = adapter.sent[0]
    assert chat_id == "999"
    assert "Commands:" in reply


def test_polling_loop_advances_offset_across_iterations(clean_db, monkeypatch):
    import packages.telegram.bot_runner as bot_runner_module

    monkeypatch.setattr(bot_runner_module, "get_session_factory", lambda: (lambda: clean_db))

    adapter = ScriptedTelegramAdapter(
        [
            [{"update_id": 5, "message": {"text": "/help", "chat": {"id": 1}}}],
            [{"update_id": 6, "message": {"text": "/help", "chat": {"id": 1}}}],
        ]
    )
    run_polling_loop(settings=_settings(), adapter=adapter, max_iterations=2)

    assert adapter.offsets_seen == [None, 6]


def test_polling_loop_skips_updates_with_no_text(clean_db, monkeypatch):
    import packages.telegram.bot_runner as bot_runner_module

    monkeypatch.setattr(bot_runner_module, "get_session_factory", lambda: (lambda: clean_db))

    adapter = ScriptedTelegramAdapter([[{"update_id": 1, "message": {"chat": {"id": 1}}}]])
    run_polling_loop(settings=_settings(), adapter=adapter, max_iterations=1)
    assert adapter.sent == []


def test_polling_loop_returns_immediately_when_telegram_not_configured(clean_db):
    run_polling_loop(settings=Settings(), max_iterations=1)
    # No adapter passed and telegram not configured -> should return without
    # attempting to construct a real HTTPTelegramAdapter or touch the network.
