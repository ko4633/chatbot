# ADR-0002: Stage 7 LLM Judge output is capped at LIKELY, never EXACT

## Status
Accepted

## Context
Entity resolution's worst failure mode is a false-positive merge: treating
two different real products as the same one silently corrupts every
downstream price comparison, margin calculation, and opportunity score for
both. The product brief explicitly calls this out (§34, §56: "데이터 부족인데
Opportunity 100점 생성" / false certainty is listed among prohibited
behaviors) and says AI should not be the "first" matching mechanism.

## Decision
`match_type = EXACT` is only ever produced by Stage 1 (deterministic
identifier equality — JAN/EAN/UPC/GTIN/ISBN/MPN/model number). No other
stage, including Stage 7 (LLM Judge), can produce `EXACT`. Stage 7's ceiling
is `LIKELY`, and `LIKELY` still requires meeting the configured merge
confidence threshold before an automatic merge into a canonical `Product`
occurs. `entity_match.evidence` and `match_stage` always record that a given
match came from the LLM judge, so it stays separately auditable/filterable
from deterministic matches even after merging.

## Consequences
- Positive: the highest-confidence claim in the system (`EXACT`) can never
  originate from a model that can hallucinate.
- Positive: false-positive merges from AI-assisted matching are isolated and
  can be bulk-reviewed/reverted by filtering on `match_stage = LLM_JUDGE`.
- Negative: some genuinely-identical products with no shared identifier and
  a very confident LLM judgment will merge as `LIKELY` rather than `EXACT`,
  which is a cosmetic distinction only — `LIKELY` still merges above
  threshold. No functional opportunity is lost, only a label.
