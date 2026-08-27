# OMNIS — Live Source Research (Phase 2)

Status: research only. **No live connector is implemented against any source
in this document until its findings are explicitly acted on** — this is the
gate required by `docs/MASTER_SPEC.md` §19/§51 and `CLAUDE.md` ("do not
fabricate APIs"). Everything here was checked against each provider's own
public developer documentation via web search on 2026-08-27; URLs are cited
per finding. Where this session's network policy blocked a live request
(noted per-source below), the finding is marked accordingly and the
connector stays `LIVE_CONNECTOR_PENDING` until someone verifies it from an
environment with normal internet access.

## Summary recommendation

| Domain | Recommended first connector | Why |
|---|---|---|
| FX | Frankfurter (`api.frankfurter.dev`) | No signup, no key, no quota, historical data back to 1999 — cheapest possible way to get a real "LIVE" data_mode row. Korea Eximbank as an official KRW-specific secondary once the user has a key. |
| Japan marketplace | Rakuten Ichiba Item Search API | Free registration, official, returns price/shop/genre/item-code — the closest fit to what OMNIS needs (§10/§11). |
| Korea marketplace | Naver Shopping Search API (검색 API) | Free registration, official, aggregates listings *across sellers* — matches "가격비교 서비스" better than Coupang's own APIs (see below). |

None of these are wired up as active connectors yet — see per-source
sections for exactly what's missing (mostly: the user needs to self-register
for a free key, since I cannot create third-party accounts on their behalf).

## FX providers

### Frankfurter (`api.frankfurter.dev`) — recommended
- **What it is**: an open-source, ECB-sourced exchange rate API. No API key,
  no login, no documented quota (rate-limited only against abuse).
  [Frankfurter | Free exchange rates API](https://frankfurter.dev/)
- **Coverage**: daily rates for 201 currencies (incl. JPY, KRW) sourced from
  84 central banks, historical data back to 1999.
  [Best Free Historical Exchange Rate API (2026)](https://allratestoday.com/blog/best-free-historical-exchange-rate-api-2026/)
- **Update cadence**: ECB publishes once/day (~16:00 CET) — not intraday.
  This matters for `docs/DATA_MODEL.md` FX freshness thresholds.
- **Caveat (why this is still LIVE_CONNECTOR_PENDING, not wired up live)**:
  this session's network egress policy blocked both `WebFetch` and a direct
  `curl` to `frankfurter.dev`/`api.frankfurter.dev`, so the exact current
  request/response shape could not be empirically re-verified in this
  environment. `packages/fx/frankfurter_provider.py` is implemented against
  Frankfurter's long-documented, stable contract (`GET /latest?from=JPY&to=KRW`
  and `GET /{date}?from=JPY&to=KRW`, JSON `{"amount", "base", "date", "rates"}`)
  but is **not** the default provider — it requires
  `FX_PROVIDER=frankfurter` to activate, and its docstring tells whoever
  flips that switch to confirm the live shape against
  `https://frankfurter.dev` first. This is the honest middle ground between
  "implement nothing" and "assert an unverified contract is confirmed live."

### 한국수출입은행 (Korea Eximbank) Open API — official KRW-specific alternative
- **What it is**: Korea's official public-data exchange rate API.
  [한국수출입은행 환율 정보 | 공공데이터포털](https://www.data.go.kr/data/3068846/openapi.do)
- **Access**: requires registering on the Korea Eximbank Open API portal and
  completing identity verification to get an auth key — a manual step only
  the account owner can do.
  [한국수출입은행 환율 API 신청방법](https://wetoz.kr/html/board.php?bo_table=tipntech&wr_id=313&sca=API)
- **Limits**: 1,000 calls/day; daily rates published ~11:00 KST on business
  days (not intraday, no weekend/holiday updates).
- **Recommendation**: good second provider once the user has a key (adds an
  official-KRW-source cross-check against Frankfurter's ECB-derived cross
  rate) — implement when/if requested, not blocking for Phase 2.

## Japan marketplace

### Rakuten Ichiba Item Search API — recommended candidate
- **Official, documented**: [Rakuten Web Service: Rakuten Ichiba Item Search API](https://webservice.rakuten.co.jp/documentation/ichiba-item-search)
- **Auth**: free developer registration; as of the Feb-2026 migration, both
  `application_id` and `access_key` are required (version `20260701`).
- **Data returned**: keyword/genre/shop/item-code search → item name, price,
  shop name, genre, item code, review info — a strong match for
  `NormalizedListing` (packages/collectors/types.py).
- **Not recommended**: Amazon Japan PA-API — Amazon has stopped onboarding
  new PA-API customers and is deprecating it on 2026-05-15 in favor of a
  "Creators API"; it also requires an existing Associates account with sales
  history to keep access.
  [Amazon Product API (PA-API) in 2026: Restrictions](https://dev.to/agenthustler/amazon-product-api-pa-api-in-2026-restrictions-alternatives-and-web-scraping-4l35)
  Not viable as a first connector.
- **Secondary candidate**: Yahoo!ショッピング Product Search API — official,
  free `Client ID` registration, search by keyword/JAN/genre/brand/store.
  [Yahoo!デベロッパーネットワーク ショッピングAPI](https://developer.yahoo.co.jp/webapi/shopping/)

## Korea marketplace

### Naver Shopping 검색 API (Search API) — recommended candidate
- **Official, documented**: [네이버 검색 API - 쇼핑](https://developers.naver.com/docs/serviceapi/search/shopping/shopping.md)
- **Auth**: free `Client ID` + `Client Secret`, sent as HTTP headers — no
  login flow, no OAuth.
- **Data returned**: shopping search results aggregated across many malls —
  this is the "가격비교" behavior OMNIS actually needs (comparing what
  multiple KR sellers charge for the same product), unlike the two Coupang
  APIs below.

### Coupang — investigated, **not recommended** as the first KR connector
Two different Coupang APIs exist and neither fits cleanly:
- **Coupang Open API** (`developers.coupangcorp.com` / `developers.coupang.com`):
  this is a **seller/vendor (Wing) API** for merchants to manage *their own*
  registered product listings, orders, and shipping — not a general
  catalog/price-search API for arbitrary competitors' listings.
  [Product API - 쿠팡 Open API](https://developers.coupangcorp.com/hc/en-us/sections/360004260614-Product-API)
  Using it for market-wide price discovery would be using it outside its
  intended purpose.
- **쿠팡파트너스 (Coupang Partners) API**: an affiliate/deep-link API.
  Explicitly does **not** support price or sort filter parameters, and its
  search endpoint is capped at **10 calls/hour**.
  [쿠팡파트너스 검색 API 호출 제한 및 가격 필터링 이슈](https://velog.io/@shwj203/%EC%BF%A0%ED%8C%A1%ED%8C%8C%ED%8A%B8%EB%84%88%EC%8A%A4-%EA%B2%80%EC%83%89-API-%ED%98%B8%EC%B6%9C-%EC%A0%9C%ED%95%9C-%EB%B0%8F-%EA%B0%80%EA%B2%A9-%ED%95%84%ED%84%B0%EB%A7%81-%EC%9D%B4%EC%8A%88)
  10 requests/hour cannot support anything beyond a trivial demo — not
  usable as a real collector cadence.
- **Recommendation**: revisit Coupang only if Naver Shopping coverage proves
  insufficient for a specific product category; do not build against either
  Coupang API as the primary KR source.

## What Phase 2 actually implements from this research

- `packages/collectors/base.py`'s existing `Collector` interface already
  fits all of the above (collect/parse/normalize/validate) — no core change
  needed to add a real connector later, confirming ARCHITECTURE.md §1's
  design goal held up.
- No JP/KR marketplace connector is implemented yet — all four candidates
  above need a human to self-register for a free key first. Fixture
  collectors remain the only JP/KR sources.
- FX gets one real, if not-yet-network-verified, provider
  (`FrankfurterFXProvider`) behind an opt-in flag, plus the
  `ManualFXProvider` (fixture/config-driven) as the default — see
  `docs/ADR/0006-fx-provider-architecture.md`.

## Next step for the user

To turn any of these into an actual live connector:
1. Register for the free key (Rakuten / Naver / Yahoo! JP / Korea Eximbank —
   all are self-service, a few minutes each).
2. Put the key in `.env` (a new variable, never `NEXT_PUBLIC_*`).
3. Ask for that specific connector to be implemented — at that point real
   requests can be tested from your machine (this sandbox's network policy
   cannot reach any of these domains to verify a live implementation).
