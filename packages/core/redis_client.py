"""Redis is used for exactly one thing in Phase 1: a simple lock preventing
two AnalysisRun pipelines from running concurrently (docs/ARCHITECTURE.md §6
Adversarial Review: duplicate job execution). It is not used as a general
cache or queue yet — that's Phase 2 scope (docs/ROADMAP.md) once scheduling
actually needs one; adding it speculatively now would be exactly the
premature abstraction CLAUDE.md tells us to avoid.
"""

from __future__ import annotations

from contextlib import contextmanager

import redis

from packages.core.errors import OmnisError
from packages.core.settings import Settings, get_settings

ANALYSIS_RUN_LOCK_KEY = "omnis:analysis_run:lock"
LOCK_TTL_SECONDS = 3600


class AnalysisRunAlreadyInProgress(OmnisError):
    pass


def get_redis_client(settings: Settings | None = None) -> redis.Redis:
    settings = settings or get_settings()
    return redis.Redis(host=settings.redis_host, port=settings.redis_port, decode_responses=True)


@contextmanager
def analysis_run_lock(client: redis.Redis | None = None):
    client = client or get_redis_client()
    acquired = client.set(ANALYSIS_RUN_LOCK_KEY, "1", nx=True, ex=LOCK_TTL_SECONDS)
    if not acquired:
        raise AnalysisRunAlreadyInProgress("another analysis run is already in progress")
    try:
        yield
    finally:
        client.delete(ANALYSIS_RUN_LOCK_KEY)
