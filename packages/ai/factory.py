from __future__ import annotations

from packages.ai.anthropic_provider import AnthropicProvider
from packages.ai.base import AIProvider
from packages.ai.null_provider import NullAIProvider
from packages.core.settings import Settings, get_settings


def get_ai_provider(settings: Settings | None = None) -> AIProvider:
    """The only place that decides which AIProvider backs the system.

    Falls back to NullAIProvider whenever AI is not both enabled AND keyed
    (docs/AI_POLICY.md §6) — the backend/worker must never fail to boot for
    lack of an AI key.
    """
    settings = settings or get_settings()
    if settings.ai_effectively_enabled:
        return AnthropicProvider(api_key=settings.anthropic_api_key)
    return NullAIProvider()
