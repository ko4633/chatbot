# OMNIS — Security

## 1. Trust boundary

```
Browser (apps/web)  --https-->  OMNIS Backend (apps/api)  --https-->  AI / external APIs
```

The browser never holds, sends, or receives an AI provider key or a
marketplace API key. There is no `NEXT_PUBLIC_OPENAI_KEY` /
`NEXT_PUBLIC_ANTHROPIC_KEY` style variable anywhere in this repo, and there
must never be one — any PR introducing a `NEXT_PUBLIC_*` secret is a
security bug, not a style nit.

## 2. Secrets

- Local dev: `.env` (gitignored). `.env.example` lists every variable name
  the app reads, with a placeholder or empty value — never a real key.
- `apps/web` reads only `NEXT_PUBLIC_API_BASE_URL` (a URL, not a secret) at
  build/runtime.
- Production: out of scope for Phase 1 (single-user local system), but the
  architecture does not block swapping `.env` loading for a secret manager
  (AWS Secrets Manager / GCP Secret Manager / Vault) later — `packages/core/settings.py`
  is the single place secrets are read from the environment; a secret-manager
  backed `Settings` loader is a drop-in replacement for that one module.

## 3. Logging

`packages/observability/redact.py` scrubs any structured log field whose key
matches `*key*`, `*token*`, `*secret*`, `*password*`, `*authorization*`
(case-insensitive) before it is emitted, replacing the value with
`***REDACTED***`. This runs in the logging formatter itself, not at each call
site, so a developer forgetting to redact manually cannot leak a secret.
HTTP client instrumentation (AI provider calls) logs request metadata
(latency, status, token counts) and never the request/response body verbatim
when that body could contain the API key in a header.

## 4. Input handling

- All API request/response bodies are Pydantic 2.x models — no untyped dict
  passthrough across the HTTP boundary.
- SQLAlchemy 2.x ORM / parameterized queries only; no raw string-interpolated
  SQL anywhere in the codebase.
- Collector-parsed HTML/JSON is never `eval`'d or executed; parsing uses
  `BeautifulSoup`/`lxml`/`json.loads` only.
- Raw fetched bytes stored in the data lake are stored as opaque blobs
  (content-hash addressed) and never re-served to the frontend directly —
  the frontend only ever sees data that has passed through
  normalize/validate.

## 5. AuthN/AuthZ

Phase 1 is single-user, run locally by its owner. There is no multi-tenant
auth system yet, and none is faked — the API does not pretend to have
per-user access control it does not enforce. `user_email` fields exist on
`UserDecision`/`WatchlistItem` as real columns (not derived from a fake
session) so adding real auth later is additive, not a schema break. This gap
is listed explicitly in `docs/ROADMAP.md` and `KNOWN_RISKS` in the build
report — it is not silently assumed away.

## 6. Dependency and supply chain

Backend dependencies are pinned in `apps/api/requirements.txt` /
`pyproject.toml`; frontend in `apps/web/package-lock.json`. No dependency is
added to fetch code at runtime from an unpinned source. Docker images are
based on official upstream images (`python:3.12-slim`, `node:20-alpine`,
`postgres:16`, `redis:7`, `minio/minio`) — no unnecessary custom base images.

## 7. Rate limiting / abuse

Out of scope for Phase 1 (local single-user, fixture collectors only, no live
external calls). When live marketplace connectors are added (Phase 2, see
`docs/ROADMAP.md`), each `Collector` must declare a rate limit and respect
robots.txt/ToS before being merged — enforced by code review checklist, not
yet by tooling.

## 8. Threat model summary (Phase 1)

| Threat | Mitigation |
|---|---|
| AI/marketplace key leaked via frontend bundle | No secret ever reaches `apps/web`; architecturally impossible, not just avoided |
| Key leaked via logs | Structured-log redaction at the formatter level |
| Key committed to git | `.env` gitignored, `.env.example` has placeholders only, pre-commit awareness in `CLAUDE.md` |
| SQL injection | ORM-only, parameterized queries |
| Malicious HTML in a fixture/collector response | Parsed with a real parser, never executed; stored as opaque blob, never rendered raw in the browser |
| Mock data mistaken for live and acted on | `Source.is_mock`, UI badge, `X-Omnis-Data-Mode` response header (see ARCHITECTURE.md §6) |
