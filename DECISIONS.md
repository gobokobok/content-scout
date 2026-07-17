# DECISIONS — content-scout

Binding decisions. Add an entry before deviating from any of these.

| # | Date | Decision | Rationale |
|---|---|---|---|
| D1 | 2026-07-17 | MVP platform is Instagram only; YouTube/TikTok/Threads later behind the same `Platform` interface | Focus; IG is the user's primary need |
| D2 | 2026-07-17 | IG data via **Apify actors** (pay-per-result) | Fastest to MVP, managed infra, usage-based cost maps onto token metering; own scraper rejected as anti-bot arms race |
| D3 | 2026-07-17 | Summaries from **caption + cover image** via Claude Haiku 4.5; no video download/transcription in MVP | ~fraction of a cent per item vs 10–50× for transcripts; transcript fetch may later become an on-shortlist action |
| D4 | 2026-07-17 | MVP auth: **email + password** (JWT); VK ID and SMS deferred, behind an auth-provider abstraction | Usage must be per-user from day 1; VK ID plugs in later |
| D5 | 2026-07-17 | Stack: FastAPI + SQLAlchemy + arq/Redis backend, Next.js 15 frontend, PostgreSQL, Railway DEV/PROD | Python fits scraping/LLM pipelines; user's standard deploy target |
| D6 | 2026-07-17 | **Personal workspace** auto-created at signup; workspace kept as a separate entity for future teams | Team features unproven; avoid migration pain later |
| D7 | 2026-07-17 | LLM: Claude (Haiku 4.5 for summaries; stronger Claude model for future scripts) | Strong Russian output, one SDK for both jobs |
| D8 | 2026-07-17 | UI **Russian-only**, all strings via next-intl from day 1 | No throwaway English pass; English = translating one file later |
| D9 | 2026-07-17 | Export format is **.xlsx** (openpyxl), not legacy .xls | Modern Excel default; user's "xls" taken as "Excel file" |
| D10 | 2026-07-17 | Every run shows a **cost estimate + confirmation** before starting | User decision; 50 accounts × 7 days is non-trivial spend |
| D11 | 2026-07-17 | Launch scale: a handful of pilot users; no rate limiting/hardening beyond basics in MVP | User decision |
| D12 | 2026-07-17 | Usage metering (`usage_events`) is written at the moment cost is incurred, from the first real run | Monetization will be token-based; retrofitting metering is error-prone |
| D13 | 2026-07-17 | Constraints: ≤50 accounts per list, run window 1–7 days, 3 lists per project (one per platform) | Product spec |
| D14 | 2026-07-17 | Views for IG photo posts/carousels are NULL (rendered "—"), never 0 | IG doesn't expose them; 0 would corrupt sorts and per-day metrics |
| D15 | 2026-07-17 | Script generation (item 7 of spec) is post-MVP; UI shows a disabled placeholder on shortlist | User marked it not-MVP |
| D16 | 2026-07-17 | UI is **responsive from day 1** (Tailwind mobile-first, every screen usable at 375px). MVP: results/shortlist tables scroll horizontally with sticky first column on mobile; post-MVP polish: card layout for tables on small screens | User requirement — mobile-friendly UI matters eventually; retrofitting responsiveness is far more expensive than building it in |
| D17 | 2026-07-17 | Mobile strategy is **Telegram Mini App wrapping the same responsive Next.js frontend**, not a native iOS/Android app. Native app deferred indefinitely, revisit only with evidence a webview genuinely can't do the job | Target users (bloggers) live in Telegram; a Mini App gives free distribution (no app store), free auth (`initData`), and free push (bot messages) with zero incremental frontend codebase — D16's mobile-first work *is* the Mini App work |
| D18 | 2026-07-17 | Post-MVP auth priority: **Telegram Login ships before VK ID** | Telegram is the natural identity for the Mini App and bot; VK ID remains queued behind it per D4's auth-provider abstraction |
| D19 | 2026-07-17 | Monetization v1 is **Telegram Stars** (in-bot/Mini-App subscription), not a Russian payment processor (ЮKassa/CloudPayments/Robokassa) | Stars requires no RU legal entity or bank integration to start charging; RU payment processor is deferred until revenue justifies the compliance overhead (see D20) |
| D20 | 2026-07-17 | Russian network-reachability plan is staged, infra-only, no code changes now: (1) pilots — no change, users have VPNs; (2) public RU launch — buy a custom domain, front Railway with a RU-hosted reverse proxy (Timeweb/Selectel VPS or RU CDN); (3) monetization/scale — move `web`+`api`+Postgres to RU cloud (Timeweb Cloud/Amvera/Yandex Cloud), keep the `worker` abroad (Railway/EU) since it's the only component calling Apify + Anthropic, bridge via WireGuard/Tailscale or the worker polling the API instead of touching RU-local DB directly | Railway isn't currently blocked in Russia but runs on foreign cloud IP ranges RKN has throttled before; 242-ФЗ requires RU citizens' personal data stored primarily in Russia at real commercial scale. The `Platform`/worker isolation already built (D1, ARCHITECTURE.md) makes stage 3 a deployment split, not a rewrite |
| D21 | 2026-07-17 | Product exposes a **stable, addressable API** (workspaces/projects/runs/shortlist_items get durable IDs) with a public-API-tokens + webhooks story queued post-MVP, to let a future content-generation product (football-content-engine-style) consume shortlisted items and (later) scripts | User's stated direction: scout finds what works, a downstream engine produces and publishes content from it — that integration should be an API contract between two products, not a merge of codebases |
