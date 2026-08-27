"""Shared exception types.

Deliberately small. A new domain-specific exception belongs in the package
that raises it (e.g. packages/ai/errors.py) unless it needs to be caught
generically across package boundaries.
"""

from __future__ import annotations


class OmnisError(Exception):
    """Base class for all OMNIS-specific exceptions."""


class ConfigurationError(OmnisError):
    """Raised when required configuration is missing or invalid."""


class NotFoundError(OmnisError):
    """Raised when a requested entity does not exist."""
