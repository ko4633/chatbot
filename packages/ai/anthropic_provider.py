"""Real Anthropic Messages API adapter. This is the only file in the
codebase allowed to know Anthropic's request/response shape (docs/AI_POLICY.md
§6). Uses httpx directly against the documented public API rather than the
`anthropic` SDK to keep the dependency footprint of "the one place that
speaks to a vendor" minimal and auditable.

embed() is intentionally NOT implemented: Anthropic does not publish a text
embeddings endpoint (see ADR-0005). Fabricating one would violate CLAUDE.md's
"do not fabricate APIs" rule. _embed_impl raises NotImplementedError, which
packages/ai/base.py turns into EmbeddingUnavailable — Stage 5 entity
resolution treats that as "stage skipped", exactly as it does when AI is
disabled outright.
"""

from __future__ import annotations

import json

import httpx

from packages.ai.base import AIProvider, _RawResult
from packages.ai.cost import resolve_model
from packages.ai.types import (
    ClassifyRequest,
    EmbedRequest,
    ExtractRequest,
    GenerateRequest,
    ReasonRequest,
)

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"


class AnthropicProvider(AIProvider):
    provider_name = "anthropic"

    def __init__(self, api_key: str, timeout_seconds: float = 30.0) -> None:
        self._api_key = api_key
        self._timeout = timeout_seconds

    def _resolve_model(self, tier: str) -> str:
        return resolve_model("anthropic", tier)

    def _call_messages(
        self, *, model: str, system: str | None, prompt: str, max_tokens: int
    ) -> _RawResult:
        headers = {
            "content-type": "application/json",
            "x-api-key": self._api_key,
            "anthropic-version": ANTHROPIC_VERSION,
        }
        body = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            body["system"] = system
        with httpx.Client(timeout=self._timeout) as client:
            response = client.post(ANTHROPIC_API_URL, headers=headers, json=body)
        response.raise_for_status()
        data = response.json()
        text = "".join(block.get("text", "") for block in data.get("content", []))
        usage = data.get("usage", {})
        return _RawResult(
            text=text,
            input_tokens=usage.get("input_tokens"),
            output_tokens=usage.get("output_tokens"),
            cached_tokens=usage.get("cache_read_input_tokens"),
        )

    def _generate_impl(self, request: GenerateRequest, model: str) -> _RawResult:
        return self._call_messages(
            model=model, system=request.system, prompt=request.prompt, max_tokens=request.max_tokens
        )

    def _reason_impl(self, request: ReasonRequest, model: str) -> _RawResult:
        prompt = f"Context:\n{request.context}\n\nQuestion:\n{request.question}"
        return self._call_messages(
            model=model, system=None, prompt=prompt, max_tokens=request.max_tokens
        )

    def _extract_impl(self, request: ExtractRequest, model: str) -> _RawResult:
        system = (
            "Extract structured fields from the given text. Respond with ONLY a JSON "
            f"object matching this shape: {request.schema_hint}. If a field is not "
            "present in the text, omit it. Do not guess values that aren't stated."
        )
        raw = self._call_messages(model=model, system=system, prompt=request.text, max_tokens=1024)
        try:
            fields = json.loads(raw.text or "{}")
        except json.JSONDecodeError:
            fields = {}
        return _RawResult(
            fields=fields,
            input_tokens=raw.input_tokens,
            output_tokens=raw.output_tokens,
            cached_tokens=raw.cached_tokens,
        )

    def _classify_impl(self, request: ClassifyRequest, model: str) -> _RawResult:
        system = (
            "Classify the given text into exactly one of these labels: "
            f"{', '.join(request.labels)}, or UNKNOWN if none clearly apply. "
            "Respond with ONLY the label, nothing else."
        )
        raw = self._call_messages(model=model, system=system, prompt=request.text, max_tokens=32)
        label = (raw.text or "").strip()
        if label not in request.labels:
            label = "UNKNOWN"
        return _RawResult(
            label=label,
            input_tokens=raw.input_tokens,
            output_tokens=raw.output_tokens,
            cached_tokens=raw.cached_tokens,
        )

    def _embed_impl(self, request: EmbedRequest, model: str) -> _RawResult:
        raise NotImplementedError(
            "Anthropic has no text embeddings API (LIVE_CONNECTOR_PENDING — see ADR-0005). "
            "Configure a dedicated embeddings provider to enable entity-resolution Stage 5."
        )
