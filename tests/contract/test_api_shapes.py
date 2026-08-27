"""Pins the API response shape so apps/web and apps/api cannot silently
drift apart (docs/EVALUATION.md §4)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app
from packages.ai.null_provider import NullAIProvider
from packages.collectors.japan_marketplace import JapanMarketplaceProvider
from packages.collectors.korea_marketplace import KoreaMarketplaceProvider
from packages.collectors.storage import LocalFileStore
from packages.intelligence.pipeline import run_full_analysis

REQUIRED_LIST_ITEM_FIELDS = {
    "id",
    "product_id",
    "product_title",
    "opportunity_score",
    "confidence_score",
    "market_pair",
    "japan_purchase_price_jpy",
    "korea_sale_price_krw",
    "expected_margin_krw",
    "kr_seller_count",
    "status",
    "is_mock",
    "data_mode",
    "created_at",
}

REQUIRED_DETAIL_FIELDS = {
    "id",
    "product_id",
    "product_title",
    "opportunity_type",
    "opportunity_score",
    "confidence_score",
    "sub_scores",
    "weights_version",
    "economics",
    "regulation_status",
    "regulation_basis",
    "status",
    "created_at",
    "analysis_run_id",
    "japan_offers",
    "korea_offers",
    "price_history_jp",
    "price_history_kr",
    "entity_matches",
    "events",
    "insights",
    "sources",
    "decisions",
    "is_mock",
    "data_mode",
    "latest_forecast",
}


@pytest.fixture
def seeded_client(clean_db, tmp_path):
    store = LocalFileStore(str(tmp_path / "raw"))
    run_full_analysis(
        clean_db,
        NullAIProvider(),
        [JapanMarketplaceProvider(), KoreaMarketplaceProvider()],
        store,
        triggered_by="pytest-contract",
    )
    return TestClient(app)


def test_health_endpoint_shape(seeded_client: TestClient):
    r = seeded_client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert {"status", "database", "ai_enabled", "environment"} <= body.keys()


def test_health_dashboard_shape(seeded_client: TestClient):
    r = seeded_client.get("/health/dashboard")
    assert r.status_code == 200
    body = r.json()
    assert {
        "status",
        "environment",
        "database",
        "redis",
        "raw_store",
        "fx",
        "collectors",
        "ai",
        "telegram",
        "data_mode",
    } <= body.keys()
    assert body["database"] == "ok"
    assert body["data_mode"] == "mock"
    assert body["fx"]["is_stale"] is False
    assert len(body["collectors"]) >= 2
    for c in body["collectors"]:
        assert {"name", "data_mode", "data_quality_status", "usable_for_opportunities"} <= c.keys()
        assert c["data_quality_status"] == "HEALTHY"
        assert c["usable_for_opportunities"] is True


def test_opportunity_list_shape_and_data_mode_header(seeded_client: TestClient):
    r = seeded_client.get("/opportunities")
    assert r.status_code == 200
    assert r.headers["x-omnis-data-mode"] == "mock"
    body = r.json()
    assert body["total"] == len(body["items"]) > 0
    for item in body["items"]:
        assert REQUIRED_LIST_ITEM_FIELDS <= item.keys()


def test_opportunity_list_excludes_stale_by_default(seeded_client: TestClient, clean_db, tmp_path):
    """A re-run of the pipeline marks the previous opportunities STALE
    (docs/EVALUATION.md §6). The default list view must show only current
    opportunities, not stale + current duplicates side by side — history
    stays reachable via ?status=STALE."""
    store = LocalFileStore(str(tmp_path / "raw2"))
    run_full_analysis(
        clean_db,
        NullAIProvider(),
        [JapanMarketplaceProvider(), KoreaMarketplaceProvider()],
        store,
        triggered_by="pytest-contract-rerun",
    )

    default_view = seeded_client.get("/opportunities").json()
    assert default_view["total"] == 4
    assert all(item["status"] != "STALE" for item in default_view["items"])

    stale_view = seeded_client.get("/opportunities", params={"status": "STALE"}).json()
    assert stale_view["total"] == 4
    assert all(item["status"] == "STALE" for item in stale_view["items"])


def test_opportunity_detail_shape(seeded_client: TestClient):
    list_body = seeded_client.get("/opportunities").json()
    opp_id = list_body["items"][0]["id"]
    r = seeded_client.get(f"/opportunities/{opp_id}")
    assert r.status_code == 200
    body = r.json()
    assert REQUIRED_DETAIL_FIELDS <= body.keys()
    # docs/ADR/0009: never a fabricated probability, never claimed calibrated.
    assert body["latest_forecast"] is not None
    assert body["latest_forecast"]["predicted_probability"] is None
    assert body["latest_forecast"]["is_calibrated"] is False


def test_opportunity_history_shape_and_point_in_time_filter(seeded_client: TestClient):
    list_body = seeded_client.get("/opportunities").json()
    opp_id = list_body["items"][0]["id"]

    full = seeded_client.get(f"/opportunities/{opp_id}/history")
    assert full.status_code == 200
    body = full.json()
    assert body["as_of"] is None
    assert body["current"] is None
    assert len(body["points"]) >= 1
    point = body["points"][0]
    assert {
        "opportunity_id",
        "analysis_run_id",
        "status",
        "opportunity_score",
        "confidence_score",
        "contribution_margin_krw",
        "jpy_krw_fx",
        "created_at",
    } <= point.keys()

    # A far-future as_of must include every point recorded so far and set
    # "current" to the most recent one (docs/MASTER_SPEC.md §6).
    future = seeded_client.get(
        f"/opportunities/{opp_id}/history", params={"as_of": "2099-01-01T00:00:00Z"}
    )
    assert future.status_code == 200
    future_body = future.json()
    assert future_body["as_of"] is not None
    assert future_body["current"] is not None
    assert len(future_body["points"]) == len(body["points"])

    # A far-past as_of must reconstruct "nothing existed yet".
    past = seeded_client.get(
        f"/opportunities/{opp_id}/history", params={"as_of": "2000-01-01T00:00:00Z"}
    )
    past_body = past.json()
    assert past_body["points"] == []
    assert past_body["current"] is None


def test_opportunity_history_404_for_unknown_id(seeded_client: TestClient):
    r = seeded_client.get("/opportunities/00000000-0000-0000-0000-000000000000/history")
    assert r.status_code == 404


def test_opportunity_detail_404_for_unknown_id(seeded_client: TestClient):
    r = seeded_client.get("/opportunities/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404


def test_decision_create_and_list_roundtrip(seeded_client: TestClient):
    opp_id = seeded_client.get("/opportunities").json()["items"][0]["id"]
    create = seeded_client.post(
        f"/opportunities/{opp_id}/decisions",
        json={"user_email": "test@example.com", "decision": "WATCH", "reason": "contract test"},
    )
    assert create.status_code == 201
    listed = seeded_client.get(f"/opportunities/{opp_id}/decisions")
    assert listed.status_code == 200
    assert any(d["reason"] == "contract test" for d in listed.json())


def test_decision_rejects_invalid_enum_value(seeded_client: TestClient):
    opp_id = seeded_client.get("/opportunities").json()["items"][0]["id"]
    r = seeded_client.post(
        f"/opportunities/{opp_id}/decisions",
        json={"user_email": "test@example.com", "decision": "NOT_A_REAL_DECISION"},
    )
    assert r.status_code == 400


def test_research_endpoint_is_honestly_not_implemented(seeded_client: TestClient):
    r = seeded_client.post("/research")
    assert r.status_code == 501


def test_search_endpoint(seeded_client: TestClient):
    r = seeded_client.get("/search", params={"q": "THERMOS"})
    assert r.status_code == 200
    assert len(r.json()["products"]) >= 1
