# ADR-0005: AnthropicProvider does not implement embed()

## Status
Accepted

## Context
`AIProvider.embed()` is part of the interface (docs/ARCHITECTURE.md §3) and
used by entity-resolution Stage 5 (embedding similarity). Anthropic's public
API does not include a text embeddings endpoint as of this build — Anthropic
publicly recommends a third-party embeddings provider (Voyage AI) instead.
CLAUDE.md forbids fabricating an API that hasn't been confirmed to exist.

## Decision
`AnthropicProvider._embed_impl` raises `NotImplementedError` with a message
naming this ADR and marking it `LIVE_CONNECTOR_PENDING`, rather than calling
a guessed or nonexistent endpoint. `packages/ai/base.py`'s `embed()` wrapper
turns this into `EmbeddingUnavailable`, which is exactly the exception
`packages/entities` Stage 5 already has to handle for the AI-disabled case —
so "no embeddings provider configured" and "AI disabled" degrade the same
way: the stage is skipped and recorded as such in `entity_match.evidence`,
never silently treated as "no match".

## Consequences
- Positive: no fabricated integration; Stage 5 is honestly unavailable until
  a real embeddings provider (Voyage AI or otherwise) is integrated as its
  own adapter implementing `AIProvider.embed()` (or a dedicated
  `EmbeddingProvider` interface, if it turns out embeddings deserve their
  own smaller Protocol — a call to make when that integration is actually
  scoped, not now).
- Negative: entity resolution in Phase 1 relies on Stages 1-4 + 7 only when
  no embeddings provider is wired up. This is acceptable for the Phase 1
  fixture dataset (see `docs/EVALUATION.md`'s golden dataset), which is
  designed so Stages 1-4 are sufficient to resolve every labeled case.
