"""The default provider when AI is disabled or no key is configured.

Never fabricates content — every _impl here raises AIDisabledError, which
packages/ai/base.py turns into either an explicit AI_DISABLED-tagged
deterministic fallback (generate/reason) or an explicit UNKNOWN/empty result
with ai_dependency=False (extract/classify), or EmbeddingUnavailable (embed).
See docs/AI_POLICY.md §6. The backend and worker must boot and run the full
non-AI pipeline with this provider — verified by
tests/integration/test_ai_disabled_pipeline.py.
"""

from __future__ import annotations

from packages.ai.base import AIProvider, _RawResult
from packages.ai.errors import AIDisabledError
from packages.ai.types import (
    ClassifyRequest,
    EmbedRequest,
    ExtractRequest,
    GenerateRequest,
    ReasonRequest,
)


class NullAIProvider(AIProvider):
    provider_name = "none"

    def _resolve_model(self, tier: str) -> str:
        return "disabled"

    def _generate_impl(self, request: GenerateRequest, model: str) -> _RawResult:
        raise AIDisabledError("AI_ENABLED=false or no API key configured")

    def _extract_impl(self, request: ExtractRequest, model: str) -> _RawResult:
        raise AIDisabledError("AI_ENABLED=false or no API key configured")

    def _classify_impl(self, request: ClassifyRequest, model: str) -> _RawResult:
        raise AIDisabledError("AI_ENABLED=false or no API key configured")

    def _reason_impl(self, request: ReasonRequest, model: str) -> _RawResult:
        raise AIDisabledError("AI_ENABLED=false or no API key configured")

    def _embed_impl(self, request: EmbedRequest, model: str) -> _RawResult:
        raise AIDisabledError("AI_ENABLED=false or no API key configured")
