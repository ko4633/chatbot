"""See docs/ADR/0010-telegram-adapter-boundary.md."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TelegramSendResult:
    sent: bool
    chat_id: str
    message_id: int | None
    error: str | None = None
