# ADR-0010: Telegram is an outbound adapter over the existing API, never a second business-logic path

## Status
Accepted

## Context
Product brief §15-17 wants Telegram broadcast (push new Opportunities to a
channel) and a personal query bot, but explicitly requires business logic
to stay in OMNIS Core with Telegram as "just" an adapter (mirrors
`packages/ai`'s and `packages/collectors`' existing adapter pattern).

## Decision
- `packages/telegram/adapter.py`: a thin `TelegramAdapter` wrapping the real
  public Telegram Bot API (`https://api.telegram.org/bot<token>/...`) —
  documented, stable, official; no fabrication risk here (unlike the
  marketplace research above, this API's contract is simple and
  well-established: `sendMessage`, `getUpdates`).
- `packages/telegram/formatter.py`: pure functions turning an `Opportunity`
  (already fully computed by `packages/scoring`/`packages/intelligence`)
  into a Telegram message string. No scoring, margin, or matching logic
  lives here — it only formats numbers that already exist.
- `packages/telegram/commands.py`: a small command router
  (`/top`, `/filter`, `/why <id>`) that calls the **same** query functions
  `apps/api` uses (`packages/intelligence`, `packages/scoring`) — it does
  not reimplement filtering/sorting logic separately from the REST API.
  This directly satisfies the brief's "Telegram Core에 비즈니스 로직을 넣지
  않는다" requirement: if `/top` and `GET /opportunities?sort_by=...` ever
  disagreed, that would itself be the bug this boundary is meant to prevent.
- `TELEGRAM_BOT_TOKEN` is read only by `packages/core/settings.py` server-side
  (docs/SECURITY.md §1) — never reaches `apps/web`, never appears in a log
  line (redacted by `packages/observability/redact.py`'s existing `*token*`
  pattern match, which already covers this without a code change).
- The bot runs as an on-demand worker command
  (`python -m apps.worker.main telegram-bot`), not a new always-on service —
  consistent with Phase 1's "no scheduler yet" decision (docs/ROADMAP.md
  Phase 2 already lists scheduling as future work); a human runs it in a
  terminal/Task Scheduler entry for now, exactly like `run-pipeline`.

## Consequences
- Positive: Telegram can be deleted entirely with zero impact on
  `apps/api`/`apps/web` — it only ever reads, never writes new derived
  state that anything else depends on.
- Positive: the "does the bot see the same numbers as the website" question
  always has the answer "yes, by construction," because both go through the
  same query functions.
- Negative: no long-running always-on bot process is set up yet (polling
  loop only runs while the worker command is running) — acceptable for
  Phase 2's scope; a real deployment (systemd/Task Scheduler/webhook mode)
  is Phase 2+ follow-up work, noted in ROADMAP.md.
