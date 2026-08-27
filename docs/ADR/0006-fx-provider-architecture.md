# ADR-0006: FX is a first-class Observation with a provider abstraction; Manual is default, Frankfurter is opt-in

## Status
Accepted

## Context
Phase 1 hardcoded a single static `jpy_krw_fx` value inside
`config/margin_assumptions.yaml`. Phase 2 requires FX to be treated as real
data: observed over time, sourced with provenance, capable of driving a
margin recomputation, and honestly labeled stale when it isn't fresh
(product brief §4-9). It also must not hard-wire OMNIS to one FX vendor.

Research (`docs/LIVE_SOURCE_RESEARCH.md`) found exactly one FX source
requiring zero registration/secret: Frankfurter (`api.frankfurter.dev`,
ECB-sourced, no key). Every other viable option (Korea Eximbank) requires a
human to self-register for a key first.

## Decision
- `fx_observation` is a new append-only table (docs/DATA_MODEL.md), same
  shape family as `price_observation` etc.: base/quote currency, rate,
  provider, `observed_at`/`retrieved_at`, source, confidence, `is_live`.
- `packages/fx/provider.py` defines an `FXProvider` Protocol
  (`get_latest`, `get_historical`), mirroring `packages/ai`'s adapter
  pattern (ARCHITECTURE.md §3) so no call site depends on a specific vendor.
- `ManualFXProvider` (config/fixture-driven, `config/fx_rates.yaml`) is the
  **default** — matches Phase 1's zero-external-dependency boot guarantee
  (docs/AI_POLICY.md §6's "must boot without a key" principle, applied here
  to FX).
- `FrankfurterFXProvider` exists and is real code against Frankfurter's
  long-documented stable contract, but is **not** the default. It activates
  only via `FX_PROVIDER=frankfurter`, because this session's network policy
  could not empirically re-verify the exact current response shape (see
  `docs/LIVE_SOURCE_RESEARCH.md`) — shipping it as the silent default would
  risk exactly the "confident but unverified" failure mode CLAUDE.md
  prohibits. Its module docstring tells whoever flips the flag to confirm
  the live shape first.
- Every FX observation written by either provider carries `is_live` (false
  for Manual, true for Frankfurter) so a UI badge and confidence scoring can
  treat them differently without inspecting the provider name.

## Consequences
- Positive: margin/opportunity scoring never has a hidden dependency on one
  FX vendor; swapping in Korea Eximbank later is a new adapter file, not a
  core change (mirrors the Collector pattern's proven benefit).
- Positive: Phase 2 ships with a genuinely live-capable FX path without
  requiring anyone to hold a secret, while being explicit that it hasn't
  been network-verified from this sandbox.
- Negative: `FrankfurterFXProvider` could still be wrong if Frankfurter's
  contract has changed since the training data this implementation drew on;
  mitigated by defaulting it off and documenting the verification step.
