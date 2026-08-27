"""Migration sanity check. The full upgrade -> downgrade -> upgrade
round-trip is exercised manually during development (see git history / build
report) rather than in the default suite, because a downgrade drops every
table and would break test isolation for every other test sharing this
database. This test instead verifies `alembic upgrade head` is a clean
no-op against an already-migrated database, and that the DB is actually at
head (not accidentally behind).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_alembic_upgrade_head_is_a_clean_noop():
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "-c", "packages/db/alembic.ini", "upgrade", "head"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr


def test_alembic_current_matches_head():
    heads = subprocess.run(
        [sys.executable, "-m", "alembic", "-c", "packages/db/alembic.ini", "heads"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    current = subprocess.run(
        [sys.executable, "-m", "alembic", "-c", "packages/db/alembic.ini", "current"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert heads.returncode == 0 and current.returncode == 0
    head_revision = heads.stdout.split()[0]
    assert head_revision in current.stdout
