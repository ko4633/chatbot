"""Collector interface. See docs/ARCHITECTURE.md §1/§5 and
docs/MASTER_SPEC.md §18 — the only place allowed to know one marketplace's
data shape. A new source means a new Collector subclass; packages/collectors
core (runner.py, storage.py, types.py) does not change.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator

from packages.collectors.types import NormalizedListing, RawFetchResult
from packages.db.enums import MarketplaceType, SourceType, TrustTier


class Collector(ABC):
    """One Collector = one source. Phase 1 collectors are fixture-based
    (LIVE_CONNECTOR_PENDING for real marketplaces — see docs/MASTER_SPEC.md §19/§51)."""

    source_name: str
    source_type: SourceType
    trust_tier: TrustTier
    market_code: str
    marketplace_name: str
    marketplace_type: MarketplaceType
    is_mock: bool = True

    @abstractmethod
    def collect(self) -> Iterator[RawFetchResult]:
        """Yield one RawFetchResult per raw item available from this source."""

    @abstractmethod
    def parse(self, raw: RawFetchResult) -> dict:
        """Turn raw bytes into a structured dict. Raises on malformed input."""

    @abstractmethod
    def normalize(self, parsed: dict) -> NormalizedListing:
        """Map this source's structured shape onto the common NormalizedListing."""

    def validate(self, listing: NormalizedListing) -> list[str]:
        """Return a list of validation problems (empty = valid). Does not
        raise — callers decide whether a problem is fatal for this listing."""
        problems: list[str] = []
        if not listing.title_raw:
            problems.append("missing title_raw")
        if listing.price_amount <= 0:
            problems.append("non-positive price_amount")
        if not listing.listing_url:
            problems.append("missing listing_url")
        return problems
