"""Default adapter when Telegram isn't configured — same boot-without-a-key
guarantee as NullAIProvider/ManualFXProvider (docs/AI_POLICY.md §6). Logs
what would have been sent instead of touching the network.
"""

from __future__ import annotations

from packages.observability.logging import get_logger
from packages.telegram.adapter import TelegramAdapter
from packages.telegram.types import TelegramSendResult

logger = get_logger(__name__)


class NullTelegramAdapter(TelegramAdapter):
    def send_message(self, chat_id: str, text: str) -> TelegramSendResult:
        logger.info("telegram_disabled_send_skipped", chat_id=chat_id, text_preview=text[:80])
        return TelegramSendResult(
            sent=False, chat_id=chat_id, message_id=None, error="telegram not configured"
        )

    def get_updates(self, offset: int | None = None, timeout_seconds: int = 30) -> list[dict]:
        return []
