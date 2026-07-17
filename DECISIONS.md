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
