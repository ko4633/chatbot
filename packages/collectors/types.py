"""The common shape every Collector must normalize into. See
docs/ARCHITECTURE.md §1 — this is the boundary: a new marketplace means a
new Collector producing this same shape, not a change to how it's persisted.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from packages.core.time_utils import utcnow
from packages.db.enums import IdentifierType, MarketplaceType


@dataclass(frozen=True)
class RawFetchResult:
    """What Collector.collect() returns for one item: the bytes to store in
    the raw data lake, plus enough metadata to write a SourceSnapshot."""

    source_url: str
    content: bytes
    mime_type: str
    retrieved_at: datetime
    succeeded: bool
    error_detail: str | None = None


@dataclass(frozen=True)
class NormalizedListing:
    market_code: str
    marketplace_name: str
    marketplace_type: MarketplaceType
    seller_external_id: str | None
    seller_name: str
    listing_url: str
    currency_code: str

    title_raw: str
    title_language: str
    brand_raw: str | None
    identifier_type: IdentifierType
    identifier_value: str | None
    model_number: str | None
    dimensions_mm: dict | None
    weight_g: int | None
    capacity: str | None
    material: str | None
    color: str | None
    pack_quantity: int | None
    attributes_extra: dict = field(default_factory=dict)

    price_amount: int = 0
    in_stock: bool = True
    stock_quantity: int | None = None
    review_count: int | None = None
    average_rating: float | None = None

    observed_at: datetime = field(default_factory=utcnow)
