# OMNIS — Project Constitution

This file governs every AI coding agent working in this repository. It is
not a style guide; it is a set of hard constraints. When any instruction
elsewhere conflicts with this file, this file wins.

Read `docs/MASTER_SPEC.md`, `docs/ARCHITECTURE.md`, and `docs/DATA_MODEL.md`
before making a non-trivial change. If a change touches the schema, also
read `docs/AI_POLICY.md` or `docs/SECURITY.md` if it's relevant to what
you're changing.

## Hard rules

- Do not guess external facts. If you don't know whether a marketplace API,
  endpoint, or HTML structure exists, say so and build against a documented
  `Provider Interface` + `Fixture`/`Mock Adapter` instead, labeled
  `LIVE_CONNECTOR_PENDING`.
- Do not fabricate APIs. Do not fabricate marketplace selectors.
- Do not hide uncertainty. A missing or low-confidence value is `UNKNOWN` or
  `null` with a reason, never a plausible-looking guess.
- Do not remove provenance. Every observation keeps its `source`,
  `source_snapshot`, `retrieved_at`, `observed_at`.
- Do not replace deterministic calculations with LLM output. FX, price,
  margin, fees, ratios, scores, dates: code computes these, always. See
  `docs/AI_POLICY.md` §3.
- Do not expose secrets. No `NEXT_PUBLIC_*` secret variables, ever. No
  secret in a log line. No secret in a commit.
- Do not silently modify public contracts. A change to an API response
  shape or a `Collector`/`AIProvider` Protocol needs an update to
  `tests/contract/` in the same change.
- Do not silently modify database schemas. Every schema change ships with
  an Alembic migration in the same change, and an update to
  `docs/DATA_MODEL.md` if the change isn't purely additive-and-obvious.
- Every significant architecture decision requires an ADR under
  `docs/ADR/`. "Significant" = changes a boundary, a data model decision, or
  a previously stated tradeoff in `docs/ARCHITECTURE.md`.
- Every external observation must retain provenance (see DATA_MODEL.md §3).
- Raw data and derived AI claims must remain distinguishable — never write
  AI output into a table that lacks `is_ai_generated`/`ai_run_id` columns.
- Inspect existing code before editing. Don't reimplement something that
  already exists elsewhere in the repo under a different name.
- Read affected specs before implementation, not after.
- Prefer small cohesive modules over one file doing everything.
- Avoid speculative abstractions that have no current use. Three similar
  lines beat a premature abstraction.
- Never disable tests merely to obtain green CI. A skip needs a checked-in
  reason (e.g. "requires AI_ENABLED=true").
- Never swallow exceptions without observability — no bare
  `except: pass`. Log with enough context to debug from the log line alone.
- Never mark mock data as live data. `Source.is_mock` must be set correctly
  for every source added.

## Development process

For every unit of work:

```
1. Inspect    — read the existing code/docs that this change touches
2. Plan       — state the approach before writing code
3. Implement  — small, cohesive changes
4. Test       — write and run the tests, don't just claim it works
5. Review diff — read your own change as if reviewing someone else's
6. Run adversarial review — what would break this? what's the failure mode?
7. Fix        — address what you found
8. Update documentation — keep docs/*.md in sync with what you actually built
```

"It probably works" is not a stopping point. Run it.

## Module boundaries (see ARCHITECTURE.md §1 for the full picture)

- `packages/scoring` never imports `packages/ai`.
- `packages/collectors` is the only place that knows a specific
  marketplace's data shape.
- `packages/ai` is the only place that imports a vendor AI SDK.
- `apps/web` never talks to the database or an AI provider directly — only
  to `apps/api`.

## When you're not sure

If a requirement is genuinely ambiguous and the two interpretations lead to
materially different schemas or user-facing behavior, say so and pick the
one that's more conservative about fabrication/certainty, rather than
guessing silently. Record the choice as an ADR if it's a real fork.
