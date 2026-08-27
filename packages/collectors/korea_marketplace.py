"""KoreaMarketplaceProvider — fixture-backed. LIVE_CONNECTOR_PENDING: no real
KR marketplace API/ToS has been verified (docs/MASTER_SPEC.md §19/§51).
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path

from packages.collectors.base import Collector
from packages.collectors.types import NormalizedListing, RawFetchResult
from packages.db.enums import IdentifierType, MarketplaceType, SourceType, TrustTier

FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "data" / "korea_marketplace.json"


class KoreaMarketplaceProvider(Collector):
    source_name = "OMNIS Fixture: Korea Marketplace"
    source_type = SourceType.FIXTURE
    trust_tier = TrustTier.MARKETPLACE
    market_code = "KR"
    marketplace_name = "Coupang-fixture"
    marketplace_type = MarketplaceType.ECOMMERCE_MARKETPLACE
    is_mock = True

    def __init__(self, fixture_path: Path = FIXTURE_PATH) -> None:
        self._fixture_path = fixture_path

    def collect(self) -> Iterator[RawFetchResult]:
        data = json.loads(self._fixture_path.read_text(encoding="utf-8"))
        for product in data["products"]:
            static_fields = {k: v for k, v in product.items() if k != "snapshots"}
            for snapshot in product["snapshots"]:
                merged = {**static_fields, **snapshot}
                content = json.dumps(merged, ensure_ascii=False).encode("utf-8")
                yield RawFetchResult(
                    source_url=product["detail_url"],
                    content=content,
                    mime_type="application/json",
                    retrieved_at=datetime.fromisoformat(snapshot["crawled_at"]),
                    succeeded=True,
                )

    def parse(self, raw: RawFetchResult) -> dict:
        if not raw.succeeded:
            raise ValueError(raw.error_detail or "fetch did not succeed")
        return json.loads(raw.content.decode("utf-8"))

    def normalize(self, parsed: dict) -> NormalizedListing:
        jan = parsed.get("jan_code")
        spec = parsed.get("spec") or {}
        dimensions_mm = None
        if {"length_mm", "width_mm", "height_mm"} <= spec.keys():
            dimensions_mm = {"l": spec["length_mm"], "w": spec["width_mm"], "h": spec["height_mm"]}
        return NormalizedListing(
            market_code=self.market_code,
            marketplace_name=self.marketplace_name,
            marketplace_type=self.marketplace_type,
            seller_external_id=parsed["store"]["code"],
            seller_name=parsed["store"]["display_name"],
            listing_url=parsed["detail_url"],
            currency_code="KRW",
            title_raw=parsed["name_ko"],
            title_language="ko",
            brand_raw=parsed.get("brand_name"),
            identifier_type=IdentifierType.JAN if jan else IdentifierType.NONE,
            identifier_value=jan,
            model_number=parsed.get("model_no"),
            dimensions_mm=dimensions_mm,
            weight_g=spec.get("weight_g"),
            capacity=None,
            material=spec.get("material"),
            color=None,
            pack_quantity=parsed.get("pack_qty"),
            attributes_extra={},
            price_amount=int(parsed["price_krw"]),
            in_stock=not bool(parsed["sold_out"]),
            stock_quantity=parsed.get("quantity_available"),
            review_count=parsed.get("review_total"),
            average_rating=parsed.get("rating_avg"),
            observed_at=datetime.fromisoformat(parsed["effective_at"]),
        )
