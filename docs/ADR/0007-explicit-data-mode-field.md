# ADR-0007: Explicit `data_mode` enum alongside `is_mock`, not a replacement for it

## Status
Accepted

## Context
Phase 1's `Source.is_mock: bool` (ADR/ARCHITECTURE.md §6) already prevents
mock data from being mistaken for live. Phase 2's product brief §12 asks for
a three-way `data_mode` (`MOCK` / `LIVE` / `MANUAL`) — a real person can also
type in a one-off observed price by hand, which is neither "mock fixture
data" nor "from an automated live connector," and collapsing that into a
boolean loses information the UI and confidence scoring both want.

## Decision
Add `DataMode` enum (`MOCK`, `LIVE`, `MANUAL`) as a new required column on
`source` (`data_mode`), populated by a migration that backfills
`data_mode = MOCK` for every existing (fixture) source — `is_mock` stays as
a generated/derived convenience (`is_mock = (data_mode == MOCK)`)
rather than being dropped, so no existing query or API contract
(`SourceRef.is_mock`) breaks. New code should read `data_mode`; `is_mock`
remains for backward compatibility within Phase 2's lifetime and is
revisited in a later ADR only if it becomes actual duplication debt.

## Consequences
- Positive: a manually-entered FX override or a manually-typed competitor
  price (e.g. a user pastes in a price they saw on their phone) has a
  correct, honest label instead of being forced into MOCK or LIVE.
- Positive: zero breaking change to Phase 1's API/UI contracts.
- Negative: two fields carrying related information for a transition period;
  acceptable, documented, and reversible.
