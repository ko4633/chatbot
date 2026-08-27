"""Frankfurter (api.frankfurter.dev) FX provider — real ECB-sourced, free,
no-API-key exchange rate service. See docs/LIVE_SOURCE_RESEARCH.md.

NOT the default provider (see docs/ADR/0006-fx-provider-architecture.md):
this session's network policy blocked both WebFetch and a direct curl to
frankfurter.dev, so the exact current request/response shape could not be
empirically re-verified from this environment. This implementation targets
Frankfurter's long-documented, stable contract:

    GET https://api.frankfurter.dev/v1/latest?base=JPY&symbols=KRW
    GET https://api.frankfurter.dev/v1/{YYYY-MM-DD}?base=JPY&symbols=KRW
    -> {"amount": 1.0, "base": "JPY", "date": "2026-08-26", "rates": {"KRW": 9.30}}

Before setting FX_PROVIDER=frankfurter in any real deployment, confirm this
shape against https://frankfurter.dev's current docs — do not trust this
docstring over the live documentation.
"""
from __future__ import annotations

from datetime import date, datetime

import httpx

from packages.core.time_utils import utcnow
from packages.fx.provider import FXProvider
from packages.fx.types import FXRateNotFound, FXRateResult

FRANKFURTER_BASE_URL = "https://api.frankfurter.dev/v1"
FRANKFURTER_CONFIDENCE = 0.9  # official ECB-sourced, but daily (not intraday) cadence


class FrankfurterFXProvider(FXProvider):
    provider_name = "frankfurter"

    def __init__(self, timeout_seconds: float = 10.0) -> None:
        self._timeout = timeout_seconds

    def _fetch(self, path: str, base: str, quote: str) -> FXRateResult:
        url = f"{FRANKFURTER_BASE_URL}/{path}"
        try:
            with httpx.Client(timeout=self._timeout) as client:
                response = client.get(url, params={"base": base.upper(), "symbols": quote.upper()})
            response.raise_for_status()
            data = response.json()
            rate = data["rates"][quote.upper()]
            observed_at = datetime.fromisoformat(data["date"])
        except (httpx.HTTPError, KeyError, ValueError) as e:
            raise FXRateNotFound(f"Frankfurter lookup failed for {base}/{quote}: {e}") from e
        return FXRateResult(
            base_currency=base.upper(),
            quote_currency=quote.upper(),
            rate=float(rate),
            observed_at=observed_at,
            retrieved_at=utcnow(),
            provider_name=self.provider_name,
            source_name="Frankfurter (api.frankfurter.dev, ECB-sourced)",
            confidence=FRANKFURTER_CONFIDENCE,
            is_live=True,
        )

    def get_latest(self, base: str, quote: str) -> FXRateResult:
        return self._fetch("latest", base, quote)

    def get_historical(self, base: str, quote: str, as_of: date) -> FXRateResult:
        return self._fetch(as_of.isoformat(), base, quote)
