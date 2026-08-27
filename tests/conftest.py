"""Shared pytest fixtures. Integration/contract tests need a real Postgres
(with pgvector) reachable via the standard OMNIS env vars / .env — see
docs/RUNBOOK.md. Unit tests under tests/unit do not need a database at all.
"""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from packages.db import models  # noqa: F401 - ensures metadata is populated
from packages.db.base import get_session_factory

ALL_TABLES_NEWEST_FIRST = [
    "ai_run",
    "event",
    "forecast",
    "fx_observation",
    "insight",
    "opportunity",
    "user_decision",
    "watchlist_item",
    "entity_match",
    "price_observation",
    "inventory_observation",
    "review_observation",
    "demand_observation",
    "offer",
    "product_variant",
    "product",
    "seller",
    "source_snapshot",
    "raw_object",
    "source",
    "marketplace",
    "market",
    "brand",
    "manufacturer",
    "analysis_run",
]


@pytest.fixture
def db() -> Session:
    session_factory = get_session_factory()
    session = session_factory()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def clean_db(db: Session) -> Session:
    """Truncates every OMNIS table. Use for tests that assert on exact row
    counts / exact pipeline output (docs/EVALUATION.md integration tests)."""
    table_list = ", ".join(ALL_TABLES_NEWEST_FIRST)
    db.execute(text(f"TRUNCATE {table_list} RESTART IDENTITY CASCADE"))
    db.commit()
    yield db
