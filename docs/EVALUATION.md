# OMNIS — Evaluation

## 1. What gets evaluated, and how, differ by layer

| Layer | Evaluated by |
|---|---|
| Collectors | integration tests against fixtures |
| Entity resolution | golden dataset, precision/recall/F1, **false positive rate is the headline metric** |
| Scoring (margin, opportunity, confidence) | unit tests with hand-computed expected values |
| AI-assisted features (narrative, Stage 7 judge) | `tests/evals/` — separate from correctness tests, graded on usefulness/faithfulness, not pass/fail assertions |

## 2. Golden Dataset (Entity Resolution)

`tests/fixtures/golden_entity_matches.yaml` — hand-labeled pairs of
`product_variant` fixtures with one of:

```
SAME_PRODUCT       -- must resolve to EXACT or LIKELY and merge
VARIANT            -- related but distinct SKU; must NOT merge into the same product
DIFFERENT_PRODUCT  -- must resolve to REJECTED
UNKNOWN            -- insufficient evidence either way; must resolve to POSSIBLE/UNKNOWN,
                      never forced to a confident answer
```

Measured by `tests/evals/eval_entity_resolution.py`:

```
precision = correct_matches / all_matches_made
recall    = correct_matches / all_true_matches
F1        = harmonic mean
false_positive_rate = wrong_merges / all_matches_made
```

**False positives are weighted more heavily than false negatives** in the
pass/fail gate for this suite (a missed match costs one opportunity; a wrong
merge poisons every downstream number for two unrelated products). The CI
gate: `false_positive_rate == 0` on the golden set is required to merge;
recall regressions are flagged but not auto-blocking in Phase 1 since the
golden set is small and hand-curated (documented as a known limitation).

The Phase 1 golden dataset ships with exactly the four cases required by the
product brief §46 (same product, variant, different product, ambiguous/no
identifier) plus enough near-duplicates to exercise Stages 3-5.

## 3. Scoring engine tests

`tests/unit/test_scoring.py` and `tests/unit/test_margin.py` assert exact
expected numeric output for hand-computed input/output pairs — not just "did
not throw". Every named sub-score and the margin calculator has at least one
test where the expected output was computed independently (in the test file
comments, by hand) rather than by running the function and asserting on its
own output.

## 4. Contract tests

`tests/contract/` pins the shape of `apps/api` responses (via Pydantic
schema snapshot / OpenAPI diff) so `apps/web` and `apps/api` cannot silently
drift apart. Also pins the `Collector` and `AIProvider` Protocol shapes so
adding a new collector/provider is guaranteed to satisfy what the rest of the
system expects.

## 5. AI evals (`tests/evals/`)

Not pass/fail unit tests — these record model output against a fixed input
set for human review and regression comparison across prompt versions
(`prompt_version` is part of `AIRun`, so eval results are always comparable
to the exact prompt that produced them). Phase 1 evals cover:

- Japanese product name → normalized English/Korean gloss (a handful of
  hand-picked real-world-shaped examples)
- Stage 7 LLM Judge on the golden dataset's `UNKNOWN` cases specifically —
  does it correctly abstain (return `POSSIBLE`, not force a decision) when
  deterministic stages could not decide?

These require `AI_ENABLED=true` and a real key; they are skipped (not
failed) in environments without one, and this must show up as `SKIPPED` in
test output, never silently passed.

## 6. Opportunity outcome evaluation (forward-looking, Phase 2+)

`opportunity` rows retain `sub_scores`/`economics`/`confidence_score` at
creation time immutably (Phase 1 does not recompute in place — a
re-analysis creates a new `analysis_run` and, if warranted, an
`OPPORTUNITY_SCORE_CHANGE` event referencing both). This is what makes the
brief's "what changed since we recommended this" and "how did last month's
picks actually turn out" questions answerable without a dedicated
evaluation table yet — the raw material already exists in `opportunity` +
`event` + `user_decision`. A dedicated `opportunity_outcome` materialization
(tracking `future_price`, `future_competition`, `outcome`) is Phase 2 scope,
listed in `docs/ROADMAP.md`, once there is more than one analysis run's
worth of history to evaluate against.

## 7. Test pyramid location

```
tests/unit/          pure functions: scoring, margin, entity-match stage logic
tests/integration/   DB + collectors + pipeline, real Postgres (docker), fixture data
tests/contract/      API/Provider/Collector shape pinning
tests/fixtures/      shared fixture data + golden dataset
tests/evals/         AI-assisted feature evaluation (skippable without a key)
```

No test is skipped or deleted to obtain a green run; a skip must have an
explicit, checked-in reason (`@pytest.mark.skipif(not settings.ai_enabled, ...)`
is acceptable, a bare `@pytest.mark.skip` is not).
