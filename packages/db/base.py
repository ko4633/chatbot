"""SQLAlchemy 2.x engine/session/declarative base.

Synchronous SQLAlchemy is used deliberately for Phase 1 (see docs/RUNBOOK.md
and ADR discussion in ARCHITECTURE.md): FastAPI endpoints run sync DB code in
FastAPI's threadpool, which is simple, correct, and fast enough at Phase 1
data volumes. Async SQLAlchemy is a valid future optimization, not a
correctness requirement, so it is not adopted speculatively (CLAUDE.md:
avoid speculative abstractions).
"""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from packages.core.settings import get_settings


class Base(DeclarativeBase):
    pass


def make_engine(database_url: str | None = None):
    url = database_url or get_settings().database_url
    return create_engine(url, pool_pre_ping=True, future=True)


_engine = None
_SessionLocal: sessionmaker[Session] | None = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = make_engine()
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine(), autoflush=False, expire_on_commit=False)
    return _SessionLocal


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: yields a session, always closes it."""
    session_factory = get_session_factory()
    db = session_factory()
    try:
        yield db
    finally:
        db.close()
