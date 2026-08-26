from __future__ import annotations

from packages.core.errors import OmnisError


class AIDisabledError(OmnisError):
    """Raised by generate()/reason() when AI is disabled and no safe
    deterministic fallback text was provided by the caller."""


class EmbeddingUnavailable(OmnisError):
    """Raised by embed() when no embedding could be produced (AI disabled,
    provider does not support embeddings, or the call failed). Callers
    (entity resolution Stage 5) must treat this as 'stage skipped', never as
    'no match found'. See docs/AI_POLICY.md §6.
    """


class AIProviderError(OmnisError):
    """A real (non-disabled) AI provider call failed. Always recorded as an
    AIRun(status=FAILED) before being raised — see packages/ai/base.py."""
