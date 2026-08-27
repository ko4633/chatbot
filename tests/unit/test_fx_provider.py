"""ManualFXProvider reads config/fx_rates.yaml only — no network call, no
external key required (docs/ADR/0006, same boot-without-a-key guarantee as
NullAIProvider). See docs/AI_POLICY.md §6 for the pattern this mirrors.
"""

from __future__ import annotations

from datetime import date

import pytest

from packages.fx.manual_provider import ManualFXProvider
from packages.fx.types import FXRateNotFound

provider = ManualFXProvider()


def test_get_latest_returns_configured_rate():
    result = provider.get_latest("JPY", "KRW")
    assert result.rate == pytest.approx(9.30)
    assert result.is_live is False
    assert result.base_currency == "JPY"
    assert result.quote_currency == "KRW"


def test_get_latest_is_case_insensitive_on_currency_codes():
    result = provider.get_latest("jpy", "krw")
    assert result.rate == pytest.approx(9.30)


def test_get_latest_unknown_pair_raises_not_fabricates():
    # GBP/KRW isn't in config/fx_rates.yaml — must raise, never interpolate
    # or guess a plausible-looking rate (CLAUDE.md hard rule).
    with pytest.raises(FXRateNotFound):
        provider.get_latest("GBP", "KRW")


def test_get_historical_returns_closest_observation_at_or_before_date():
    result = provider.get_historical("JPY", "KRW", date(2026, 8, 10))
    # config/fx_rates.yaml history: 2026-08-05 -> 9.36 is the latest point
    # at or before 2026-08-10; 2026-08-12's point must NOT be used.
    assert result.rate == pytest.approx(9.36)


def test_get_historical_before_all_data_raises():
    with pytest.raises(FXRateNotFound):
        provider.get_historical("JPY", "KRW", date(2020, 1, 1))
