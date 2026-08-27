"""Default FX provider: reads config/fx_rates.yaml. Zero external
dependency, same "must boot without a key" guarantee as NullAIProvider
(docs/AI_POLICY.md §6) applied to FX. See docs/ADR/0006."""
from __future__ import annotations

from datetime import date, datetime
from functools import lru_cache
from pathlib import Path

import yaml

from packages.core.time_utils import utcnow
from packages.fx.provider import FXProvider
from packages.fx.types import FXRateNotFound, FXRateResult

CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "fx_rates.yaml"
MANUAL_CONFIDENCE = 0.7  # fixture data — real but not live-market-verified


@lru_cache
def _load_config() -> dict:
    with CONFIG_PATH.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def _pair_key(base: str, quote: str) -> str:
    return f"{base.upper()}/{quote.upper()}"


class ManualFXProvider(FXProvider):
    provider_name = "manual"

    def get_latest(self, base: str, quote: str) -> FXRateResult:
        config = _load_config()
        pair = config.get("pairs", {}).get(_pair_key(base, quote))
        if pair is None:
            raise FXRateNotFound(f"No manual FX data configured for {base}/{quote}")
        latest = pair["latest"]
        return FXRateResult(
            base_currency=base.upper(),
            quote_currency=quote.upper(),
            rate=float(latest["rate"]),
            observed_at=datetime.fromisoformat(latest["observed_at"]),
            retrieved_at=utcnow(),
            provider_name=self.provider_name,
            source_name="Manual FX (config/fx_rates.yaml)",
            confidence=MANUAL_CONFIDENCE,
            is_live=False,
        )

    def get_historical(self, base: str, quote: str, as_of: date) -> FXRateResult:
        config = _load_config()
        pair = config.get("pairs", {}).get(_pair_key(base, quote))
        if pair is None:
            raise FXRateNotFound(f"No manual FX data configured for {base}/{quote}")
        candidates = [
            point
            for point in pair.get("history", [])
            if datetime.fromisoformat(point["observed_at"]).date() <= as_of
        ]
        if not candidates:
            raise FXRateNotFound(f"No manual FX observation for {base}/{quote} at or before {as_of}")
        closest = max(candidates, key=lambda p: p["observed_at"])
        return FXRateResult(
            base_currency=base.upper(),
            quote_currency=quote.upper(),
            rate=float(closest["rate"]),
            observed_at=datetime.fromisoformat(closest["observed_at"]),
            retrieved_at=utcnow(),
            provider_name=self.provider_name,
            source_name="Manual FX (config/fx_rates.yaml)",
            confidence=MANUAL_CONFIDENCE,
            is_live=False,
        )
