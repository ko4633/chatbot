# npm audit findings (apps/web) — investigation and remediation plan

Phase 2 directive: do not run `npm audit fix --force` blindly. This
document is the required investigation before any decision.

## Summary

`npm audit` (run from `apps/web`) reports **5 high severity** advisories
across 3 packages. All 5 require a Next.js major-version bump to resolve —
there is no available patch/minor release that fixes any of them while
staying on Next.js 14.x. `npm audit fix --force` would jump straight to
`next@16.3.3`, two major versions ahead of the currently pinned `^14.2.5`
(resolved: `14.2.35`, itself the newest release on the 14.x line — there is
no newer 14.2.x that fixes these).

## Dependency tree

```
omnis-web@0.1.0
+-- eslint-config-next@14.2.35 (devDependency)
|   `-- @next/eslint-plugin-next@14.2.35
|       `-- glob@10.3.10          <- flagged (dev-only)
+-- eslint@8.57.1 (devDependency, unrelated to the flagged advisories)
`-- next@14.2.35 (dependency)      <- flagged (prod)
    `-- postcss@8.4.31             <- flagged (prod, transitive via next)
```

## Per-package assessment

### 1. `glob@10.3.10` — dev-only, low real-world risk here
- **Advisory**: command injection in the `glob` CLI's `-c/--cmd` flag
  (GHSA-5j98-mcp5-4vw2) — executes matched paths with `shell: true`.
- **Reachable from**: `eslint-config-next` -> `@next/eslint-plugin-next`,
  a devDependency. `glob` is used here as a *library* (to expand file
  globs during lint), never invoked as its own CLI with untrusted input.
  Nothing in this repo shells out to the `glob` binary.
- **Prod impact**: none — devDependency, never bundled or shipped.
- **Risk here**: negligible. The vulnerable code path (the CLI's `-c` flag)
  is not exercised by anything in this project.

### 2. `next@14.2.35` — prod dependency, needs case-by-case read
- **Advisories** (11 listed) span Server Components/Server Actions,
  Middleware, the Image Optimizer, and cache-key collisions.
- **Actual feature usage in this app** (checked directly, not assumed):
  - No `middleware.ts`/`middleware.js` anywhere in `apps/web`.
  - No `"use server"` Server Actions anywhere in `app/` or `lib/`.
  - No `next/image` usage anywhere (the app renders plain data, no images).
  - `next.config.js` sets only `reactStrictMode: true` — no
    `images.remotePatterns`, no custom rewrites, no i18n config.
  - App Router with client-side `fetch()` calls to a separate FastAPI
    backend (`apps/api`) — no React Server Components data-fetching
    patterns that the cache-poisoning/cache-confusion advisories target.
- **Reading**: every advisory whose trigger is Middleware, Server Actions,
  `next/image` remotePatterns, or RSC cache-key collisions is **not
  currently reachable** by this codebase's actual feature usage. That is a
  statement about current exposure, not a reason to stop tracking the
  advisories — a future change that adds Middleware or Server Actions
  would need to re-check this list before shipping.
- **Prod impact if exploited**: would require the app to first adopt one of
  the affected features (Middleware, Server Actions, next/image
  remotePatterns) — none of which requires a version bump to add later
  and re-triggers this same assessment at that time.

### 3. `postcss@8.4.31` — prod dependency, transitive via `next` itself
- **Advisories**: XSS via unescaped `</style>` in stringified output;
  arbitrary local file read via `sourceMappingURL` in CSS comments (two
  related GHSAs); path traversal in previous-sourcemap auto-loading.
- **Reachable from**: Next.js's own internal CSS build pipeline processes
  this repo's own checked-in CSS (`apps/web/app/globals.css` and
  colocated styles) at build time — not arbitrary user-supplied CSS at
  runtime. The XSS/file-read vectors require processing **attacker-
  controlled** CSS content or sourcemap comments, which this app's build
  never does (no user-submitted stylesheets, no dynamic CSS from
  untrusted input).
- **Risk here**: low under current usage, same caveat as above — this
  reflects what the app does today, not a permanent exemption.

## Why not `npm audit fix --force` right now

- It jumps `next` from 14.2.35 -> 16.3.3 (two majors) and
  `eslint-config-next` to a matching 16.x release in one shot, with zero
  in-between verification.
- Next.js 15 raised the minimum React peer dependency to React 19 (this
  app is on React 18.3.1) and changed several APIs (async `cookies()`/
  `headers()`/`params`, revised caching defaults). Next.js 16 layers
  further changes on top. Neither has been validated against this
  codebase — `apps/web` has no owned test suite exercising server-render
  behavior beyond `next build`/`tsc --noEmit` (see Known Risks in the
  final BUILD STATUS report), so a two-major jump could silently break
  the running app without a failing test ever catching it.
- CLAUDE.md and this directive both explicitly require investigating
  before acting, not treating "audit fix has a flag for it" as
  sufficient justification for a breaking change to a production
  dependency the whole frontend rests on.

## Recommended staged plan (not executed in this session — needs a
dedicated upgrade + verification pass)

1. **Now (zero risk, but not applied automatically here either)**: none of
   the three findings has a same-major fix available, so there is nothing
   safe to patch in place today without also touching `next`. This is
   itself worth recording: the "safe partial fix" that exists for many
   audit findings does not exist for this one.
2. **Next step, scheduled as its own change**: evaluate `next@15.3.9`
   (the `next-15-3` dist-tag — the newest 15.x release, one major version
   away rather than two) as an intermediate target:
   - Bump `react`/`react-dom` to whatever 15.3.9 requires, confirm the
     peer-dependency story first (`npm info next@15.3.9 peerDependencies`).
   - Run `npm run build` and `npx tsc --noEmit` and manually re-verify the
     two pages (`/` and `/opportunities/[id]`) render correctly against a
     running `apps/api`.
   - Re-run `npm audit` after the bump — 15.3.9 may still carry some of
     the same advisories if they were never fixed on the 15.x line either
     (needs re-checking at that time, not assumed here).
3. **Only after 15.x is verified stable**: consider 16.x, repeating the
   same verification gate.
4. Track this document's staged plan in `docs/ROADMAP.md` as a Phase 2+
   follow-up rather than closing it silently.

## Bottom line

- 0 of 5 findings are fixable without a Next.js major-version bump.
- All 5 target feature surfaces (Middleware, Server Actions, `next/image`
  remotePatterns, RSC cache internals, CSS/sourcemap processing of
  untrusted input) that this app does not currently use — verified by
  direct inspection of `apps/web`, not assumed.
- Recommendation: schedule a dedicated Next.js 14 -> 15 upgrade (not 16
  directly) as its own change with a real verification pass, rather than
  forcing it inside this Phase 2 change alongside everything else.
