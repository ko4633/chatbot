"""Long-polling personal bot loop (docs/ADR/0010). Runs as an on-demand
worker command (`python -m apps.worker.main telegram-bot`), not an
always-on service — same "no scheduler yet" scope as the rest of Phase 2
(docs/ROADMAP.md).
"""

from __future__ import annotations

from packages.core.settings import Settings, get_settings
from packages.db.base import get_session_factory
from packages.observability.logging import get_logger
from packages.telegram.adapter import TelegramAdapter
from packages.telegram.commands import dispatch_command
from packages.telegram.factory import get_telegram_adapter

logger = get_logger(__name__)


def run_polling_loop(
    settings: Settings | None = None,
    adapter: TelegramAdapter | None = None,
    max_iterations: int | None = None,
) -> None:
    """max_iterations is None for the real long-running loop; tests pass a
    finite number so this function actually returns."""
    settings = settings or get_settings()
    if not settings.telegram_effectively_enabled:
        logger.warning("telegram_bot_not_configured")
        return

    adapter = adapter or get_telegram_adapter(settings)
    session_factory = get_session_factory()
    offset: int | None = None
    iterations = 0

    while max_iterations is None or iterations < max_iterations:
        updates = adapter.get_updates(offset=offset, timeout_seconds=30)
        db = session_factory()
        try:
            for update in updates:
                offset = update["update_id"] + 1
                message = update.get("message") or {}
                text = message.get("text")
                chat_id = str(message.get("chat", {}).get("id", ""))
                if not text or not chat_id:
                    continue
                reply = dispatch_command(db, chat_id, text)
                adapter.send_message(chat_id, reply)
        finally:
            db.close()
        iterations += 1
