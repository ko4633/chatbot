"""docs/DATA_MODEL.md §5: running the same collector twice must not
duplicate rows. Requires a real Postgres — see tests/conftest.py."""

from __future__ import annotations

from packages.collectors.japan_marketplace import JapanMarketplaceProvider
from packages.collectors.korea_marketplace import KoreaMarketplaceProvider
from packages.collectors.runner import run_collector
from packages.collectors.storage import LocalFileStore
from packages.db.models.observations import PriceObservation
from packages.db.models.offer import Offer
from packages.db.models.product import ProductVariant


def _row_counts(db):
    return (
        db.query(ProductVariant).count(),
        db.query(Offer).count(),
        db.query(PriceObservation).count(),
    )


def test_running_collectors_twice_is_idempotent(clean_db, tmp_path):
    store = LocalFileStore(str(tmp_path / "raw"))

    run_collector(clean_db, JapanMarketplaceProvider(), store)
    run_collector(clean_db, KoreaMarketplaceProvider(), store)
    clean_db.commit()
    first_counts = _row_counts(clean_db)
    assert first_counts[0] > 0  # sanity: something was actually ingested

    run_collector(clean_db, JapanMarketplaceProvider(), store)
    run_collector(clean_db, KoreaMarketplaceProvider(), store)
    clean_db.commit()
    second_counts = _row_counts(clean_db)

    assert second_counts == first_counts


def test_broken_fixture_item_does_not_abort_the_run(clean_db, tmp_path):
    store = LocalFileStore(str(tmp_path / "raw"))
    stats = run_collector(clean_db, JapanMarketplaceProvider(), store)
    clean_db.commit()
    assert stats.items_failed == 1  # the intentionally-broken jp-006 listing
    assert stats.items_succeeded > 0  # every other JP listing still ingested
