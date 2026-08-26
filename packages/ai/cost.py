"""Loads config/ai_models.yaml: task-tier -> model id, and cost-per-token
estimates. See docs/AI_POLICY.md §7."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "ai_models.yaml"


@lru_cache
def load_ai_model_config() -> dict:
    with CONFIG_PATH.open() as f:
        return yaml.safe_load(f)


def resolve_model(provider: str, tier: str) -> str:
    config = load_ai_model_config()
    try:
        return config[provider][tier]
    except KeyError as e:
        raise KeyError(f"No model configured for provider={provider!r} tier={tier!r}") from e


def estimate_cost_usd(
    model: str, input_tokens: int | None, output_tokens: int | None
) -> float | None:
    config = load_ai_model_config()
    pricing = config.get("pricing_usd_per_1k_tokens", {}).get(model)
    if pricing is None or input_tokens is None or output_tokens is None:
        return None
    return (input_tokens / 1000) * pricing["input"] + (output_tokens / 1000) * pricing["output"]
