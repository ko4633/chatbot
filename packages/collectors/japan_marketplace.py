"""JapanMarketplaceProvider — fixture-backed. LIVE_CONNECTOR_PENDING: no real
JP marketplace API/ToS has been verified, so this reads a bundled fixture
file rather than fetching anything over the network (docs/MASTER_SPEC.md §19/§51).
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path

from packages.collectors.base import Collector
from packages.collectors.types import NormalizedListing, RawFetchResult
from packages.core.time_utils import utcnow
from packages.db.enums import IdentifierType, MarketplaceType, SourceType, TrustTier

FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "data" / "japan_marketplace.json"


class JapanMarketplaceProvider(Collector):
    source_name = "OMNIS Fixture: Japan Marketplace"
    source_type = SourceType.FIXTURE
    trust_tier = TrustTier.MARKETPLACE
    market_code = "JP"
    marketplace_name = "Rakuten-fixture"
    marketplace_type = MarketplaceType.ECOMMERCE_MARKETPLACE
    is_mock = True

    def __init__(self, fixture_path: Path = FIXTURE_PATH) -> None:
        self._fixture_path = fixture_path

    def collect(self) -> Iterator[RawFetchResult]:
        data = json.loads(self._fixture_path.read_text(encoding="utf-8"))
        for listing in data["listings"]:
            if listing.get("simulate_fetch_failure"):
                yield RawFetchResult(
                    source_url=listing["url"],
                    content=b"",
                    mime_type="application/json",
                    retrieved_at=utcnow(),
                    succeeded=False,
                    error_detail="simulated fetch timeout (fixture)",
                )
                continue
            static_fields = {k: v for k, v in listing.items() if k != "snapshots"}
            for snapshot in listing["snapshots"]:
                merged = {**static_fields, **snapshot}
                content = json.dumps(merged, ensure_ascii=False).encode("utf-8")
                yield RawFetchResult(
                    source_url=listing["url"],
                    content=content,
                    mime_type="application/json",
                    retrieved_at=datetime.fromisoformat(snapshot["retrieved_at"]),
                    succeeded=True,
                )

    def parse(self, raw: RawFetchResult) -> dict:
        if not raw.succeeded:
            raise ValueError(raw.error_detail or "fetch did not succeed")
        return json.loads(raw.content.decode("utf-8"))

    def normalize(self, parsed: dict) -> NormalizedListing:
        jan = parsed.get("jan")
        return NormalizedListing(
            market_code=self.market_code,
            marketplace_name=self.marketplace_name,
            marketplace_type=self.marketplace_type,
            seller_external_id=parsed["seller"]["id"],
            seller_name=parsed["seller"]["name"],
            listing_url=parsed["url"],
            currency_code="JPY",
            title_raw=parsed["title"],
            title_language="ja",
            brand_raw=parsed.get("brand"),
            identifier_type=IdentifierType.JAN if jan else IdentifierType.NONE,
            identifier_value=jan,
            model_number=parsed.get("model_number"),
            dimensions_mm=parsed.get("dimensions_mm"),
            weight_g=parsed.get("weight_g"),
            capacity=parsed.get("capacity"),
            material=parsed.get("material"),
            color=parsed.get("color"),
            pack_quantity=parsed.get("pack_quantity"),
            attributes_extra={},
            price_amount=int(parsed["price_jpy"]),
            in_stock=bool(parsed["in_stock"]),
            stock_quantity=parsed.get("stock_quantity"),
            review_count=parsed.get("review_count"),
            average_rating=parsed.get("average_rating"),
            observed_at=datetime.fromisoformat(parsed["observed_at"]),
        )
