from __future__ import annotations

from packages.core.settings import Settings, get_settings
from packages.telegram.adapter import TelegramAdapter
from packages.telegram.null_adapter import NullTelegramAdapter


def get_telegram_adapter(settings: Settings | None = None) -> TelegramAdapter:
    """The only place that decides which TelegramAdapter backs the system —
    mirrors packages/ai/factory.py and packages/fx/factory.py. Falls back to
    NullTelegramAdapter whenever Telegram isn't both enabled AND keyed; the
    backend/worker must never fail to boot for lack of a bot token."""
    settings = settings or get_settings()
    if settings.telegram_effectively_enabled:
        from packages.telegram.http_adapter import HTTPTelegramAdapter

        return HTTPTelegramAdapter(bot_token=settings.telegram_bot_token)
    return NullTelegramAdapter()
