from __future__ import annotations

from packages.core.settings import Settings, get_settings
from packages.fx.manual_provider import ManualFXProvider
from packages.fx.provider import FXProvider


def get_fx_provider(settings: Settings | None = None) -> FXProvider:
    """ManualFXProvider is the default — matches the "boots without any
    external key" guarantee (docs/ADR/0006). FX_PROVIDER=frankfurter opts
    into the not-yet-network-verified live provider."""
    settings = settings or get_settings()
    if settings.fx_provider == "frankfurter":
        from packages.fx.frankfurter_provider import FrankfurterFXProvider

        return FrankfurterFXProvider()
    return ManualFXProvider()
