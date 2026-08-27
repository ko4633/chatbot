# OMNIS — Master Specification

Status: Phase 1 (Product Intelligence Foundation)
Last updated: 2026-08-26

## 1. What OMNIS is

OMNIS is a personal Intelligence Operating System. It continuously observes
public information sources, preserves where every fact came from, links the
same real-world entity across sources, tracks how things change over time,
cross-checks claims against multiple sources, and surfaces opportunities that
are actually worth a human's attention and action.

OMNIS is **not** a scraper, a news summarizer, a price comparator, or a RAG
chatbot, even though it uses techniques from all of those. Those are
components. The product is the discovery and evidence trail on top of them.

## 2. First use case: Japan → Korea Product Opportunity Discovery

The only use case implemented end-to-end in Phase 1: find products that can
plausibly be bought/imported from Japan and resold in Korea at a profit, with
full evidence, a deterministic economics model, and an explicit confidence
score that is never confused with the opportunity score itself.

Everything else in this document (general entity model, multi-domain roadmap,
autonomous research) is architecture that must not be *blocked* by Phase 1
decisions, but is not implemented in Phase 1. See `docs/ROADMAP.md`.

## 3. Non-negotiable product principles

Ranked, because they conflict with "ship more features fast" and the ranking
is how conflicts get resolved:

1. **Accuracy** — a wrong recommendation is worse than no recommendation.
2. **Traceability** — every number must be attributable to where it came from.
3. **Provenance preservation** — raw sources are never discarded or silently edited.
4. **Extensibility** — the schema and interfaces must not block Phase 2+ domains.
5. **Failure isolation** — one bad source/collector/job must not take down the system.
6. **Hallucination suppression** — AI output is never stored or treated as an observed fact.
7. **Decision value** — success is measured by "would a human have found this by
   searching?", not by volume of data collected.

The system's success metric is explicitly **not** "how much data did we collect".
It is: did OMNIS surface something a manual search would have missed, and can
every step of the reasoning be walked back to evidence?

## 4. Information layers

```
RAW DATA → OBSERVATION → FACT → EVENT → INSIGHT → OPPORTUNITY → DECISION
```

See `docs/DATA_MODEL.md` §2 for the exact tables and mapping. Summary:

- **Raw Data**: unmodified fetched bytes (HTML/JSON/PDF/image), content-addressed
  in the raw data lake. Table: `RawObject`.
- **Observation**: one measured value at one point in time, with provenance.
  Tables: `PriceObservation`, `InventoryObservation`, `ReviewObservation`,
  `DemandObservation`.
- **Fact**: a normalized, current-state view derived from observations
  (e.g. "latest known price"). Not a separate table in Phase 1 — a queried
  projection over Observations, because materializing it separately would
  create a second source of truth. See ADR-0004.
- **Event**: a detected change between two points in time. Table: `Event`.
- **Insight**: a cross-cutting interpretation connecting multiple facts/events.
  Table: `Insight`.
- **Opportunity**: an actionable candidate with a score and a confidence.
  Table: `Opportunity`.
- **Decision**: what the user actually chose to do about it. Table: `UserDecision`.

## 5. Documents in this set

| Doc | Purpose |
|---|---|
| `docs/MASTER_SPEC.md` | This file — product intent and non-negotiables |
| `docs/ARCHITECTURE.md` | System architecture, module boundaries, adversarial review |
| `docs/DATA_MODEL.md` | Full entity/table design, provenance, time model |
| `docs/AI_POLICY.md` | What AI may and may not decide, provider abstraction |
| `docs/SECURITY.md` | Secret handling, trust boundaries, threat model |
| `docs/EVALUATION.md` | How scoring, matching, and AI features are evaluated |
| `docs/ROADMAP.md` | Phase 2-6 and why the schema doesn't block them |
| `docs/RUNBOOK.md` | Operating the system day to day |
| `docs/ADR/*.md` | Individual architecture decisions and why |
| `CLAUDE.md` | Project constitution for AI coding agents working on this repo |

## 6. Definition of done for Phase 1

See `docs/ROADMAP.md` §Phase 1 for the full checklist. In one sentence: a user
runs the stack locally, seeds the Japan/Korea fixture dataset, and can see and
fully audit a computed import/resale opportunity from raw source to final
score, with mock data clearly labeled as mock everywhere it appears.
