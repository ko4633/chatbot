"""FXProvider interface — mirrors packages/ai's adapter pattern
(docs/ARCHITECTURE.md §3) so no call site depends on a specific FX vendor.
See docs/ADR/0006-fx-provider-architecture.md."""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

from packages.fx.types import FXRateResult


class FXProvider(ABC):
    provider_name: str

    @abstractmethod
    def get_latest(self, base: str, quote: str) -> FXRateResult:
        """Most recent known rate. Raises FXRateNotFound if the pair isn't covered."""

    @abstractmethod
    def get_historical(self, base: str, quote: str, as_of: date) -> FXRateResult:
        """Rate as of a specific date (or the most recent prior observation —
        FX is not published every calendar day). Raises FXRateNotFound if no
        observation exists at or before as_of; never extrapolates."""
