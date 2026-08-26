"""Request/result types for the AIProvider interface. See docs/ARCHITECTURE.md §3."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from packages.db.enums import AIRunPurpose


@dataclass(frozen=True)
class GenerateRequest:
    purpose: AIRunPurpose
    prompt: str
    prompt_version: str
    system: str | None = None
    deterministic_fallback: str | None = None  # used verbatim if AI is disabled
    model_tier: str = "standard"
    analysis_run_id: uuid.UUID | None = None
    max_tokens: int = 1024


@dataclass(frozen=True)
class GenerateResult:
    text: str
    ai_run_id: uuid.UUID
    ai_generated: bool  # False when this is a deterministic fallback, not a model output


@dataclass(frozen=True)
class ExtractRequest:
    purpose: AIRunPurpose
    text: str
    schema_hint: str
    prompt_version: str
    model_tier: str = "cheap"
    analysis_run_id: uuid.UUID | None = None


@dataclass(frozen=True)
class ExtractResult:
    fields: dict
    ai_run_id: uuid.UUID
    ai_dependency: bool


@dataclass(frozen=True)
class ClassifyRequest:
    purpose: AIRunPurpose
    text: str
    labels: list[str]
    prompt_version: str
    model_tier: str = "cheap"
    analysis_run_id: uuid.UUID | None = None


@dataclass(frozen=True)
class ClassifyResult:
    label: str  # "UNKNOWN" when AI disabled or inconclusive
    ai_run_id: uuid.UUID
    ai_dependency: bool


@dataclass(frozen=True)
class ReasonRequest:
    purpose: AIRunPurpose
    question: str
    context: str
    prompt_version: str
    deterministic_fallback: str | None = None
    model_tier: str = "premium"
    analysis_run_id: uuid.UUID | None = None
    max_tokens: int = 1024


@dataclass(frozen=True)
class ReasonResult:
    answer: str
    ai_run_id: uuid.UUID
    ai_generated: bool


@dataclass(frozen=True)
class EmbedRequest:
    purpose: AIRunPurpose
    text: str
    prompt_version: str
    analysis_run_id: uuid.UUID | None = None


@dataclass(frozen=True)
class EmbedResult:
    vector: list[float]
    ai_run_id: uuid.UUID
    dimensions: int = field(default=0)
