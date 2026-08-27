"""Structured-log redaction (docs/SECURITY.md §3).

Runs in the logging formatter itself so a developer forgetting to redact
manually at a call site cannot leak a secret.
"""

from __future__ import annotations

import re
from typing import Any

_SENSITIVE_KEY_PATTERN = re.compile(r"(key|token|secret|password|authorization)", re.IGNORECASE)
REDACTED = "***REDACTED***"


def redact_event(_logger: object, _method_name: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    """structlog processor: redact any field whose key looks sensitive."""
    for key in list(event_dict.keys()):
        if _SENSITIVE_KEY_PATTERN.search(key):
            event_dict[key] = REDACTED
    return event_dict
