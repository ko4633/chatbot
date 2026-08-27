"""Real Telegram Bot API adapter (docs/ADR/0010). `sendMessage`/`getUpdates`
are long-documented, stable, official public endpoints — unlike the
marketplace research in docs/LIVE_SOURCE_RESEARCH.md, this API's contract
carries no fabrication risk (CLAUDE.md's "don't guess an endpoint" concern
doesn't apply to a widely-used, unchanged-for-years public interface).

Network access to api.telegram.org could not be verified from this
development sandbox (the same outbound-network-policy block seen against
api.frankfurter.dev in packages/fx/frankfurter_provider.py) — verify this
against a real bot token before relying on it in production. Labeled
LIVE_CONNECTOR_PENDING per CLAUDE.md until then.
"""

from __future__ import annotations

import httpx

from packages.observability.logging import get_logger
from packages.telegram.adapter import TelegramAdapter
from packages.telegram.types import TelegramSendResult

logger = get_logger(__name__)

TELEGRAM_API_BASE = "https://api.telegram.org"


class HTTPTelegramAdapter(TelegramAdapter):
    def __init__(self, bot_token: str, timeout_seconds: float = 30.0) -> None:
        self._token = bot_token
        self._timeout = timeout_seconds

    def _url(self, method: str) -> str:
        return f"{TELEGRAM_API_BASE}/bot{self._token}/{method}"

    def send_message(self, chat_id: str, text: str) -> TelegramSendResult:
        try:
            with httpx.Client(timeout=self._timeout) as client:
                response = client.post(
                    self._url("sendMessage"),
                    json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
                )
            response.raise_for_status()
            data = response.json()
            message_id = data.get("result", {}).get("message_id")
            return TelegramSendResult(sent=True, chat_id=chat_id, message_id=message_id)
        except Exception as e:  # noqa: BLE001 - a broadcast/reply failure must never crash the caller
            logger.error("telegram_send_failed", chat_id=chat_id, error=str(e))
            return TelegramSendResult(sent=False, chat_id=chat_id, message_id=None, error=str(e))

    def get_updates(self, offset: int | None = None, timeout_seconds: int = 30) -> list[dict]:
        params: dict = {"timeout": timeout_seconds}
        if offset is not None:
            params["offset"] = offset
        with httpx.Client(timeout=timeout_seconds + 10) as client:
            response = client.get(self._url("getUpdates"), params=params)
        response.raise_for_status()
        return response.json().get("result", [])
