from __future__ import annotations

from collections.abc import Generator

from sqlalchemy.orm import Session

from packages.ai.base import AIProvider
from packages.ai.factory import get_ai_provider
from packages.core.settings import get_settings
from packages.db.base import get_db as _get_db


def get_db() -> Generator[Session, None, None]:
    yield from _get_db()


def get_ai() -> AIProvider:
    return get_ai_provider(get_settings())
