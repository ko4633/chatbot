"""TelegramAdapter: the only two operations OMNIS needs from Telegram —
sending a message and polling for new ones. Mirrors packages/ai/base.py and
packages/fx/provider.py's adapter-interface shape (docs/ADR/0010).
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from packages.telegram.types import TelegramSendResult


class TelegramAdapter(ABC):
    @abstractmethod
    def send_message(self, chat_id: str, text: str) -> TelegramSendResult: ...

    @abstractmethod
    def get_updates(self, offset: int | None = None, timeout_seconds: int = 30) -> list[dict]: ...
