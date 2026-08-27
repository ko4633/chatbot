# ADR-0003: Confidence is not a weighted component of the Opportunity Score

## Status
Accepted

## Context
The product brief contains two statements that are in tension:

- §14 gives an example `opportunity_weights` YAML that includes a
  `confidence: 0.10` key as one of the components summed into the final
  Opportunity Score.
- §15 states, with a worked example ("Opportunity Score = 93, Confidence
  Score = 31" must not be treated as a strong recommendation), that
  Confidence must be tracked as an axis independent of the Opportunity
  Score, and lists the specific inputs that should drive Confidence
  (source count, reliability, freshness, identifier match, missing/
  conflicting data, sample size, AI dependency, market coverage).

If Confidence were literally blended into the Opportunity Score as one of
its weighted components, the §15 scenario (high score, low confidence)
becomes structurally harder to produce and easier to misread, since part of
"low confidence" would already have dragged the score down — defeating the
purpose of keeping them separate and legible.

## Decision
`config/opportunity_weights.yaml` does not include a `confidence` key. The
Opportunity Score is a weighted sum over exactly: `demand`, `competition`,
`price_gap`, `margin`, `trend`, `supply`, `logistics`, `regulation`.
`confidence_score` is computed by a separate, independent function
(`packages/scoring/confidence.py`) using the inputs §15 actually lists, and
stored in its own `opportunity.confidence_score` column. §14's example YAML
is treated as illustrative ("위 값은 예시일 뿐이다" — the brief says so
directly), and §15's requirement, which is more specific and has a worked
example demonstrating exactly the failure this ADR avoids, is treated as
the binding rule when the two are in conflict.

## Consequences
- Positive: the "high score, low confidence" case the brief explicitly wants
  representable stays fully representable and legible in the UI as two
  separate numbers.
- Positive: `packages/scoring` for the Opportunity Score itself has no
  dependency on data-quality/provenance metadata — it only needs the eight
  substantive sub-scores — while confidence scoring is free to evolve its
  own formula without touching the opportunity weight config.
- Negative: implementation deviates from the literal example config in the
  original product brief. Called out explicitly here and in
  `docs/ARCHITECTURE.md` §6 so it reads as a resolved inconsistency, not an
  overlooked requirement.
