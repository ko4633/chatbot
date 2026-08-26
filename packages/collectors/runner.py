"""Generic collector-run persistence. Not marketplace-specific — this is
what makes "add a collector" not require touching core (docs/ARCHITECTURE.md
§1/§18). Idempotent: a SourceSnapshot's natural key (source_id, source_url,
retrieved_at) gates whether an item's Observations get (re-)written; Offer/
ProductVariant are get-or-created keyed by (marketplace_id, listing_url), so
re-running the same ingestion job twice does not create duplicate rows
(docs/DATA_MODEL.md §5, docs/ARCHITECTURE.md §6 Adversarial Review).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from packages.collectors.base import Collector
from packages.collectors.storage import RawObjectStore
from packages.collectors.types import NormalizedListing
from packages.db.enums import (
    ExtractionMethod,
    MarketplaceType,
    ReliabilityLevel,
    SnapshotStatus,
)
from packages.db.models.catalog import Market, Marketplace, Seller
from packages.db.models.observations import (
    InventoryObservation,
    PriceObservation,
    ReviewObservation,
)
from packages.db.models.offer import Offer
from packages.db.models.product import ProductVariant
from packages.db.models.raw_object import RawObject
from packages.db.models.source import Source, SourceSnapshot
from packages.observability.logging import get_logger

logger = get_logger(__name__)

COLLECTOR_ALGORITHM_VERSION = "collectors.v1"
FIXTURE_CONFIDENCE = 1.0  # deterministic: fixture data has no extraction uncertainty


@dataclass
class CollectorRunStats:
    items_seen: int = 0
    items_succeeded: int = 0
    items_failed: int = 0
    items_skipped_duplicate: int = 0
    observations_written: int = 0
    errors: list[str] = field(default_factory=list)


def get_or_create_source(db: Session, collector: Collector) -> Source:
    source = db.query(Source).filter_by(name=collector.source_name).one_or_none()
    if source:
        return source
    source = Source(
        name=collector.source_name,
        source_type=collector.source_type,
        trust_tier=collector.trust_tier,
        factual_reliability=ReliabilityLevel.MEDIUM,
        signal_value=ReliabilityLevel.HIGH,
        country=collector.market_code,
        base_url=None,
        is_mock=collector.is_mock,
        is_active=True,
    )
    db.add(source)
    db.flush()
    return source


def _get_or_create_market(db: Session, code: str) -> Market:
    market = db.query(Market).filter_by(code=code).one_or_none()
    if market:
        return market
    currency = {"JP": "JPY", "KR": "KRW"}.get(code, "USD")
    market = Market(code=code, name=code, currency_code=currency)
    db.add(market)
    db.flush()
    return market


def _get_or_create_marketplace(
    db: Session, market: Market, name: str, marketplace_type: MarketplaceType
) -> Marketplace:
    marketplace = db.query(Marketplace).filter_by(market_id=market.id, name=name).one_or_none()
    if marketplace:
        return marketplace
    marketplace = Marketplace(market_id=market.id, name=name, marketplace_type=marketplace_type)
    db.add(marketplace)
    db.flush()
    return marketplace


def _get_or_create_seller(
    db: Session, marketplace: Marketplace, listing: NormalizedListing
) -> Seller:
    seller = (
        db.query(Seller)
        .filter_by(marketplace_id=marketplace.id, external_seller_id=listing.seller_external_id)
        .one_or_none()
    )
    if seller:
        seller.last_seen_at = max(seller.last_seen_at, listing.observed_at)
        return seller
    seller = Seller(
        marketplace_id=marketplace.id,
        external_seller_id=listing.seller_external_id,
        name=listing.seller_name,
        first_seen_at=listing.observed_at,
        last_seen_at=listing.observed_at,
    )
    db.add(seller)
    db.flush()
    return seller


def _get_or_create_raw_object(db: Session, ref) -> RawObject:
    obj = db.query(RawObject).filter_by(content_hash=ref.content_hash).one_or_none()
    if obj:
        return obj
    obj = RawObject(
        content_hash=ref.content_hash,
        mime_type=ref.mime_type,
        byte_size=ref.byte_size,
        storage_path=ref.storage_path,
    )
    db.add(obj)
    db.flush()
    return obj


def _get_or_create_variant_and_offer(
    db: Session,
    market: Market,
    marketplace: Marketplace,
    seller: Seller,
    listing: NormalizedListing,
) -> tuple[ProductVariant, Offer]:
    offer = (
        db.query(Offer)
        .filter_by(marketplace_id=marketplace.id, listing_url=listing.listing_url)
        .one_or_none()
    )
    if offer:
        offer.last_seen_at = max(offer.last_seen_at, listing.observed_at)
        variant = db.get(ProductVariant, offer.product_variant_id)
        assert variant is not None
        return variant, offer

    variant = ProductVariant(
        product_id=None,
        market_id=market.id,
        title_raw=listing.title_raw,
        title_language=listing.title_language,
        brand_raw=listing.brand_raw,
        identifier_type=listing.identifier_type,
        identifier_value=listing.identifier_value,
        model_number=listing.model_number,
        dimensions_mm=listing.dimensions_mm,
        weight_g=listing.weight_g,
        capacity=listing.capacity,
        material=listing.material,
        color=listing.color,
        pack_quantity=listing.pack_quantity,
        attributes_extra=listing.attributes_extra,
    )
    db.add(variant)
    db.flush()
    offer = Offer(
        product_variant_id=variant.id,
        marketplace_id=marketplace.id,
        seller_id=seller.id,
        listing_url=listing.listing_url,
        currency_code=listing.currency_code,
        first_seen_at=listing.observed_at,
        last_seen_at=listing.observed_at,
    )
    db.add(offer)
    db.flush()
    return variant, offer


def _snapshot_already_ingested(
    db: Session, source_id: uuid.UUID, source_url: str, retrieved_at
) -> bool:
    return (
        db.query(SourceSnapshot)
        .filter_by(source_id=source_id, source_url=source_url, retrieved_at=retrieved_at)
        .first()
        is not None
    )


def run_collector(
    db: Session, collector: Collector, raw_store: RawObjectStore
) -> CollectorRunStats:
    stats = CollectorRunStats()
    source = get_or_create_source(db, collector)
    market = _get_or_create_market(db, collector.market_code)
    marketplace = _get_or_create_marketplace(
        db, market, collector.marketplace_name, collector.marketplace_type
    )

    for raw in collector.collect():
        stats.items_seen += 1

        if not raw.succeeded:
            stats.items_failed += 1
            stats.errors.append(f"{raw.source_url}: {raw.error_detail}")
            db.add(
                SourceSnapshot(
                    source_id=source.id,
                    source_url=raw.source_url,
                    retrieved_at=raw.retrieved_at,
                    raw_object_id=None,
                    parser_name=collector.__class__.__name__,
                    parser_version=COLLECTOR_ALGORITHM_VERSION,
                    extraction_method=ExtractionMethod.FIXTURE,
                    status=SnapshotStatus.FAILED,
                    error_detail=raw.error_detail,
                )
            )
            db.flush()
            logger.warning(
                "collector_item_failed", source_url=raw.source_url, error=raw.error_detail
            )
            continue

        if _snapshot_already_ingested(db, source.id, raw.source_url, raw.retrieved_at):
            stats.items_skipped_duplicate += 1
            continue

        try:
            parsed = collector.parse(raw)
            listing = collector.normalize(parsed)
            problems = collector.validate(listing)
        except Exception as e:  # noqa: BLE001 - one bad item must not abort the run
            stats.items_failed += 1
            stats.errors.append(f"{raw.source_url}: {e}")
            db.add(
                SourceSnapshot(
                    source_id=source.id,
                    source_url=raw.source_url,
                    retrieved_at=raw.retrieved_at,
                    raw_object_id=None,
                    parser_name=collector.__class__.__name__,
                    parser_version=COLLECTOR_ALGORITHM_VERSION,
                    extraction_method=ExtractionMethod.FIXTURE,
                    status=SnapshotStatus.FAILED,
                    error_detail=str(e),
                )
            )
            db.flush()
            logger.error("collector_parse_failed", source_url=raw.source_url, error=str(e))
            continue

        ref = raw_store.put(raw.content, raw.mime_type)
        raw_object = _get_or_create_raw_object(db, ref)
        status = SnapshotStatus.SUCCESS if not problems else SnapshotStatus.PARTIAL
        snapshot = SourceSnapshot(
            source_id=source.id,
            source_url=listing.listing_url,
            retrieved_at=raw.retrieved_at,
            raw_object_id=raw_object.id,
            parser_name=collector.__class__.__name__,
            parser_version=COLLECTOR_ALGORITHM_VERSION,
            extraction_method=ExtractionMethod.FIXTURE,
            status=status,
            error_detail="; ".join(problems) if problems else None,
        )
        db.add(snapshot)
        db.flush()

        seller = _get_or_create_seller(db, marketplace, listing)
        variant, offer = _get_or_create_variant_and_offer(db, market, marketplace, seller, listing)

        common_provenance = dict(
            source_id=source.id,
            source_snapshot_id=snapshot.id,
            retrieved_at=raw.retrieved_at,
            observed_at=listing.observed_at,
            parser_name=collector.__class__.__name__,
            parser_version=COLLECTOR_ALGORITHM_VERSION,
            extraction_method=ExtractionMethod.FIXTURE,
            confidence=FIXTURE_CONFIDENCE,
        )
        db.add(
            PriceObservation(
                offer_id=offer.id,
                price_amount=listing.price_amount,
                currency_code=listing.currency_code,
                **common_provenance,
            )
        )
        db.add(
            InventoryObservation(
                offer_id=offer.id,
                in_stock=listing.in_stock,
                stock_quantity=listing.stock_quantity,
                **common_provenance,
            )
        )
        stats.observations_written += 2
        if listing.review_count is not None:
            db.add(
                ReviewObservation(
                    product_variant_id=variant.id,
                    review_count=listing.review_count,
                    average_rating=listing.average_rating,
                    **common_provenance,
                )
            )
            stats.observations_written += 1

        db.flush()
        stats.items_succeeded += 1

    return stats
