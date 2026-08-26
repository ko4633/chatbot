"""ID generation. UUIDv4, generated application-side (see docs/DATA_MODEL.md §1)."""

from __future__ import annotations

import uuid


def new_id() -> uuid.UUID:
    return uuid.uuid4()
