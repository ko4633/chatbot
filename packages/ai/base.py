"""Base AIProvider: every public method records exactly one AIRun row before
returning, regardless of which concrete adapter is used. See
docs/ARCHITECTURE.md §3 and docs/AI_POLICY.md §7 — cost tracking cannot be
bypassed by calling the adapter differently, because it happens here, not in
each adapter implementation.
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod

from sqlalchemy.orm import Session

from packages.ai.errors import AIDisabledError, AIProviderError, EmbeddingUnavailable
from packages.ai.types import (
    ClassifyRequest,
    ClassifyResult,
    EmbedRequest,
    EmbedResult,
    ExtractRequest,
    ExtractResult,
    GenerateRequest,
    GenerateResult,
    ReasonRequest,
    ReasonResult,
)
from packages.core.time_utils import utcnow
from packages.db.enums import AIRunStatus
from packages.db.models.run import AIRun


class _RawResult:
    """Internal: what a concrete adapter's _impl method returns."""

    def __init__(
        self,
        text: str | None = None,
        fields: dict | None = None,
        label: str | None = None,
        vector: list[float] | None = None,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        cached_tokens: int | None = None,
    ) -> None:
        self.text = text
        self.fields = fields
        self.label = label
        self.vector = vector
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.cached_tokens = cached_tokens


class AIProvider(ABC):
    provider_name: str

    def _record(
        self,
        db: Session,
        *,
        purpose,
        model: str,
        prompt_version: str,
        analysis_run_id: uuid.UUID | None,
        started_at,
        status: AIRunStatus,
        raw: _RawResult | None,
        error_detail: str | None,
    ) -> AIRun:
        from packages.ai.cost import estimate_cost_usd

        completed_at = utcnow()
        cost = None
        if raw is not None:
            cost = estimate_cost_usd(model, raw.input_tokens, raw.output_tokens)
        run = AIRun(
            analysis_run_id=analysis_run_id,
            provider=self.provider_name,
            model=model,
            purpose=purpose,
            input_tokens=raw.input_tokens if raw else None,
            output_tokens=raw.output_tokens if raw else None,
            cached_tokens=raw.cached_tokens if raw else None,
            estimated_cost_usd=cost,
            started_at=started_at,
            completed_at=completed_at,
            latency_ms=int((completed_at - started_at).total_seconds() * 1000),
            status=status,
            prompt_version=prompt_version,
            error_detail=error_detail,
        )
        db.add(run)
        db.flush()
        return run

    # ---- public interface, wraps the abstract _*_impl methods ----

    def generate(self, db: Session, request: GenerateRequest) -> GenerateResult:
        started = utcnow()
        model = self._resolve_model(request.model_tier)
        try:
            raw = self._generate_impl(request, model)
            run = self._record(
                db,
                purpose=request.purpose,
                model=model,
                prompt_version=request.prompt_version,
                analysis_run_id=request.analysis_run_id,
                started_at=started,
                status=AIRunStatus.SUCCESS,
                raw=raw,
                error_detail=None,
            )
            return GenerateResult(text=raw.text or "", ai_run_id=run.id, ai_generated=True)
        except AIDisabledError as e:
            run = self._record(
                db,
                purpose=request.purpose,
                model=model,
                prompt_version=request.prompt_version,
                analysis_run_id=request.analysis_run_id,
                started_at=started,
                status=AIRunStatus.DISABLED,
                raw=None,
                error_detail=str(e),
            )
            if request.deterministic_fallback is not None:
                return GenerateResult(
                    text=f"AI_DISABLED: {request.deterministic_fallback}",
                    ai_run_id=run.id,
                    ai_generated=False,
                )
            raise
        except Exception as e:  # noqa: BLE001 - always record before surfacing
            self._record(
                db,
                purpose=request.purpose,
                model=model,
                prompt_version=request.prompt_version,
                analysis_run_id=request.analysis_run_id,
                started_at=started,
                status=AIRunStatus.FAILED,
                raw=None,
                error_detail=str(e),
            )
            raise AIProviderError(f"generate() failed: {e}") from e

    def extract(self, db: Session, request: ExtractRequest) -> ExtractResult:
        started = utcnow()
        model = self._resolve_model(request.model_tier)
        try:
            raw = self._extract_impl(request, model)
            run = self._record(
                db,
                purpose=request.purpose,
                model=model,
                prompt_version=request.prompt_version,
                analysis_run_id=request.analysis_run_id,
                started_at=started,
                status=AIRunStatus.SUCCESS,
                raw=raw,
                error_detail=None,
            )
            return ExtractResult(fields=raw.fields or {}, ai_run_id=run.id, ai_dependency=True)
        except AIDisabledError as e:
            run = self._record(
                db,
                purpose=request.purpose,
                model=model,
                prompt_version=request.prompt_version,
                analysis_run_id=request.analysis_run_id,
                started_at=started,
                status=AIRunStatus.DISABLED,
                raw=None,
                error_detail=str(e),
            )
            return ExtractResult(fields={}, ai_run_id=run.id, ai_dependency=False)
        except Exception as e:  # noqa: BLE001 - always record before surfacing
            self._record(
                db,
                purpose=request.purpose,
                model=model,
                prompt_version=request.prompt_version,
                analysis_run_id=request.analysis_run_id,
                started_at=started,
                status=AIRunStatus.FAILED,
                raw=None,
                error_detail=str(e),
            )
            raise AIProviderError(f"extract() failed: {e}") from e

    def classify(self, db: Session, request: ClassifyRequest) -> ClassifyResult:
        started = utcnow()
        model = self._resolve_model(request.model_tier)
        try:
            raw = self._classify_impl(request, model)
            run = self._record(
                db,
                purpose=request.purpose,
                model=model,
                prompt_version=request.prompt_version,
                analysis_run_id=request.analysis_run_id,
                started_at=started,
                status=AIRunStatus.SUCCESS,
                raw=raw,
                error_detail=None,
            )
            return ClassifyResult(
                label=raw.label or "UNKNOWN", ai_run_id=run.id, ai_dependency=True
            )
        except AIDisabledError as e:
            run = self._record(
                db,
                purpose=request.purpose,
                model=model,
                prompt_version=request.prompt_version,
                analysis_run_id=request.analysis_run_id,
                started_at=started,
                status=AIRunStatus.DISABLED,
                raw=None,
                error_detail=str(e),
            )
            return ClassifyResult(label="UNKNOWN", ai_run_id=run.id, ai_dependency=False)
        except Exception as e:  # noqa: BLE001 - always record before surfacing
            self._record(
                db,
                purpose=request.purpose,
                model=model,
                prompt_version=request.prompt_version,
                analysis_run_id=request.analysis_run_id,
                started_at=started,
                status=AIRunStatus.FAILED,
                raw=None,
                error_detail=str(e),
            )
            raise AIProviderError(f"classify() failed: {e}") from e

    def reason(self, db: Session, request: ReasonRequest) -> ReasonResult:
        started = utcnow()
        model = self._resolve_model(request.model_tier)
        try:
            raw = self._reason_impl(request, model)
            run = self._record(
                db,
                purpose=request.purpose,
                model=model,
                prompt_version=request.prompt_version,
                analysis_run_id=request.analysis_run_id,
                started_at=started,
                status=AIRunStatus.SUCCESS,
                raw=raw,
                error_detail=None,
            )
            return ReasonResult(answer=raw.text or "", ai_run_id=run.id, ai_generated=True)
        except AIDisabledError as e:
            run = self._record(
                db,
                purpose=request.purpose,
                model=model,
                prompt_version=request.prompt_version,
                analysis_run_id=request.analysis_run_id,
                started_at=started,
                status=AIRunStatus.DISABLED,
                raw=None,
                error_detail=str(e),
            )
            if request.deterministic_fallback is not None:
                return ReasonResult(
                    answer=f"AI_DISABLED: {request.deterministic_fallback}",
                    ai_run_id=run.id,
                    ai_generated=False,
                )
            raise
        except Exception as e:  # noqa: BLE001 - always record before surfacing
            self._record(
                db,
                purpose=request.purpose,
                model=model,
                prompt_version=request.prompt_version,
                analysis_run_id=request.analysis_run_id,
                started_at=started,
                status=AIRunStatus.FAILED,
                raw=None,
                error_detail=str(e),
            )
            raise AIProviderError(f"reason() failed: {e}") from e

    def embed(self, db: Session, request: EmbedRequest) -> EmbedResult:
        started = utcnow()
        model = self._resolve_model("standard")
        try:
            raw = self._embed_impl(request, model)
            run = self._record(
                db,
                purpose=request.purpose,
                model=model,
                prompt_version=request.prompt_version,
                analysis_run_id=request.analysis_run_id,
                started_at=started,
                status=AIRunStatus.SUCCESS,
                raw=raw,
                error_detail=None,
            )
            vector = raw.vector or []
            return EmbedResult(vector=vector, ai_run_id=run.id, dimensions=len(vector))
        except AIDisabledError as e:
            self._record(
                db,
                purpose=request.purpose,
                model=model,
                prompt_version=request.prompt_version,
                analysis_run_id=request.analysis_run_id,
                started_at=started,
                status=AIRunStatus.DISABLED,
                raw=None,
                error_detail=str(e),
            )
            raise EmbeddingUnavailable("AI disabled: no embedding available") from e
        except Exception as e:  # noqa: BLE001 - deliberately broad: any provider failure
            self._record(
                db,
                purpose=request.purpose,
                model=model,
                prompt_version=request.prompt_version,
                analysis_run_id=request.analysis_run_id,
                started_at=started,
                status=AIRunStatus.FAILED,
                raw=None,
                error_detail=str(e),
            )
            raise EmbeddingUnavailable(f"embedding call failed: {e}") from e

    # ---- adapter hooks ----

    @abstractmethod
    def _resolve_model(self, tier: str) -> str: ...

    @abstractmethod
    def _generate_impl(self, request: GenerateRequest, model: str) -> _RawResult: ...

    @abstractmethod
    def _extract_impl(self, request: ExtractRequest, model: str) -> _RawResult: ...

    @abstractmethod
    def _classify_impl(self, request: ClassifyRequest, model: str) -> _RawResult: ...

    @abstractmethod
    def _reason_impl(self, request: ReasonRequest, model: str) -> _RawResult: ...

    @abstractmethod
    def _embed_impl(self, request: EmbedRequest, model: str) -> _RawResult: ...
