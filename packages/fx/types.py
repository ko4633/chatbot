"""FX types. See docs/ADR/0006-fx-provider-architecture.md and
docs/DATA_MODEL.md `fx_observation`."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


class FXRateNotFound(Exception):
    """Raised when a provider has no rate for the requested pair/date —
    never silently extrapolated or fabricated (CLAUDE.md: no plausible-looking
    guess in place of a missing value)."""


@dataclass(frozen=True)
class FXRateResult:
    base_currency: str
    quote_currency: str
    rate: float
    observed_at: datetime
    retrieved_at: datetime
    provider_name: str
    source_name: str
    confidence: float
    is_live: bool
