# SPRINT.md — content-scout

## Sprint 1 — Walking skeleton

**Goal:** A deployed, authenticated, Russian-language shell: anyone can register on DEV, log in, and see their empty workspace. Schema and CI foundations in place for everything that follows.

**⚠️ Pre-launch reminder:** the `production` Railway environment still needs `RAILPACK_START_CMD` set per-service on `api`/`worker` (same fix just applied to `dev` — see DONE.md E1-S1 handover and ENV.md) before the first `v*` tag is pushed, or `cd.yml`'s deploy will fail the same way `deploy-dev` initially did.

**Stories (in order):**

| Story | Title | Status |
|---|---|---|
| E1-S1 | Monorepo scaffold, local env, CI, DEV deploy | done |
| E1-S2 | Database schema and migrations | done |
| E1-S3 | Email+password auth and personal workspace | done |

**Sprint 1 complete.**

Full story definitions live in `BACKLOG.md`.

## Sprint 2 — Projects & competitor lists, run lifecycle with mock data

**Stories (in order):**

| Story | Title | Status |
|---|---|---|
| E2-S1 | Project CRUD | done |
| E2-S2 | Competitor list management (IG, max 50) | done |
| E3-S1 | Run creation, cost estimate, worker skeleton | done |

**Sprint 2 complete.**

## Sprint 3 — Real Apify scraping, Claude summaries, full pipeline

**Stories (in order):**

| Story | Title | Status |
|---|---|---|
| E3-S2 | Apify Instagram integration and metrics | done |
| E4-S1 | Claude summarization service | done |
| E4-S2 | Summarization in the run pipeline | done |

**Sprint 3 complete.** The full analysis pipeline (scrape → summarize → done) runs end-to-end against real Apify + Claude on DEV.

## Sprint 4 — Results table, XLSX export, shortlist

**Stories (in order):**

| Story | Title | Status |
|---|---|---|
| E5-S1 | Results table | done |
| E5-S2 | XLSX export | done |
| E6-S1 | Shortlist | done |

**Sprint 4 complete.**

## Sprint 5 — History, usage rollups, admin view

**Stories (in order):**

| Story | Title | Status |
|---|---|---|
| E6-S2 | Run and shortlist history | done |
| E7-S1 | Usage rollups | done |
| E7-S2 | Admin usage view | in-progress (carry-over — close it first in Sprint 6) |

## Sprint 6 — Hardening, cost cuts, redesign, Telegram test launch

**Goal:** the app is safe and pleasant to share with test users **inside Telegram**: the worker survives full-size runs, strangers can't burn our Apify/Claude budget, Claude cost per item drops ~4× (D29), every screen wears the new light design system (D28), and the app opens as a Telegram Mini App from the bot with zero login friction (D27). **No payments** — Telegram Stars billing (E8-S3) comes after Sprint 6.

**Execution mode:** designed to be run back-to-back autonomously in one or few sessions (`/start-story` → `/finish-story` per story, in order, no user intervention expected). If a story blocks on a missing human prerequisite, note it in the story's Handover, skip forward if independent, and list it in the session summary.

**Human prerequisites (do BEFORE starting the sprint — see ENV.md):**
1. Create the bot: message @BotFather → `/newbot` → pick a name/handle (e.g. `content_scout_dev_bot`). Copy the token.
2. Railway `dev` environment: set `TELEGRAM_BOT_TOKEN` on **api and worker**, and `TELEGRAM_WEBHOOK_SECRET` (any random ≥32-char string) on **api**. (PROD gets its own separate bot later — not needed for Sprint 6.)
3. Railway `dev` **and** `production`: set `REGISTRATION_INVITE_CODE` on **api** (any code you'll share with test users).
   Everything else (webhook registration, menu button) is done by the stories via the Bot API.

**Stories (in order):**

| # | Story | Title | Status |
|---|---|---|---|
| 0 | E7-S2 | Admin usage view — carry-over: verify, smoke-test, finish-story | done |
| 1 | E3-S6 | Worker resilience and parallel scraping (critical bug fix) | done |
| 2 | E7-S4 | Pilot security guardrails (critical) | done |
| 3 | E4-S3 | Claude cost optimization | done |
| 4 | E12-S1 | Design system re-skin (light theme v1) | done |
| 5 | E12-S2 | Mobile cards, bottom navigation, UX states | done |
| 6 | E8-S1 | Telegram Login | done |
| 7 | E8-S5 | Telegram Mini App shell (no billing) — **sprint exit criterion** | done |
| 8 | E8-S2 | Telegram bot notifications (stretch — skip if the sprint runs long) | done |

**Sprint exit check:** open the DEV bot from a phone, tap «Открыть content-scout», run the full flow inside Telegram, and share the bot handle with a second account.

## Sprint 7 — Single-blogger MVP: Mini App fix + competitor/results depth

**Goal:** per the 2026-07-21 reprioritization (single-blogger pilot focus), close out the live-blocking Mini App bug and round out the Результаты/Конкуренты screens with the data a solo blogger actually needs to judge a competitor's content: follower counts, comments, and a relative virality signal.

**Execution mode:** same as Sprint 6 — run stories back-to-back autonomously, in dependency order, no user intervention expected.

**Stories (in order):**

| # | Story | Title | Status |
|---|---|---|---|
| 0 | E8-S6 | Telegram Mini App auto-login bootstrap fix (critical) | done |
| 1 | E5-S4 | Subscriber count next to account name | done |
| 2 | E2-S3 | Competitor profile enrichment (depends on E5-S4) | done |
| 3 | E5-S3 | Comments count column | done |
| 4 | E5-S5 | Virality score per publication (depends on E5-S4) | done |

**Sprint 7 complete.** All 5 stories from the 2026-07-21 single-blogger reprioritization shipped and CI-green (a real CI failure surfaced two bugs — a Postgres `percentile_cont`/window-function incompatibility in E5-S5, and a test-session isolation bug in E2-S3's background worker job — both fixed same-day, see their BACKLOG.md Changelog entries). Every story's DEV smoke test is still deferred (consistent with this project's established pattern — Apify/Telegram-dependent verification always waits for a real device/account); a real-device + DEV pass over all of them is still owed, tracked as a standing carry-over rather than a blocking gate.

**Also shipped in the Sprint 7 window, untracked at the time, now backfilled as stories (see DONE.md):** E12-S3 (mobile results controls consolidation — single icon row, virality badge recolor, new virality/engagement/comments sort options, export sheet copy) and E3-S7 (run scope: last-N-publications mode, alongside the existing day-window scope).

## Sprint 8 — Navigation restructure: Details, Results, Analysis (locked 2026-07-22)

**Goal:** per the 2026-07-22 execution-plan session, extend the MVP with a reshaped project IA — bottom nav collapses to three tabs (Детали/Результаты/Анализ), Детали becomes a real dashboard (KPIs, competitor/scheduled-run links, run-history cards, create-run entry), opening a run gets its own Summary+Publications detail view, and Анализ ships as a teaser for future paid deep-analysis products. This sprint reshapes the IA that Sprint 9 (scheduled runs) and Sprint 10 (monetization) both build their entry points on top of.

**Stories (in order):**

| # | Story | Title | Status |
|---|---|---|---|
| 0 | E13-S1 | Bottom nav restructure: Детали / Результаты / Анализ | done |
| 1 | E13-S2 | Details dashboard: KPI card, nav links, run-history cards, create-run entry | backlog |
| 2 | E13-S3 | Competitors page trim | backlog |
| 3 | E16-S1 | Analysis teaser page | backlog |
| 4 | E15-S1 | Run-level AI summary generation | backlog |
| 5 | E15-S2 | Top-5-posts-by-virality for a run | backlog |
| 6 | E15-S3 | Run detail page: Summary + Publications tabs | backlog |

## Sprint 9 — Scheduled runs (locked 2026-07-22)

**Goal:** recurring analysis runs on a day-of-week + time schedule, notified to Telegram on completion. First use of arq's cron scheduling in this codebase — new infra, not just new UI.

**Stories (in order):**

| # | Story | Title | Status |
|---|---|---|---|
| 0 | E14-S1 | Scheduled runs: schema and migration | backlog |
| 1 | E14-S2 | Scheduled runs: CRUD API + arq cron dispatcher | backlog |
| 2 | E14-S3 | Scheduled Runs page (list + create/edit) | backlog |
| 3 | E14-S4 | Wire Run-now / Schedule choice into Details' create-run flow | backlog |
| 4 | E14-S5 | Telegram notification for scheduled-run completion | backlog |

## Sprint 10 — Monetization: 1990₽/mo subscription (locked 2026-07-22, D30)

**Goal:** first paid tier — 1990₽/month for 2000 tokens via Telegram Stars (D19), credited onto the existing `User.token_balance` column. Placed after Sprint 8 so the subscription entry point has a UI home (profile/settings, not the 3-tab bottom nav).

**Stories (in order):**

| # | Story | Title | Status |
|---|---|---|---|
| 0 | E8-S3 | Telegram Stars subscriptions (re-scoped per D30 — single tier) | backlog |

## Sprint plan (projection, adjust at each /sprint-review)

- **Sprint 2:** E2-S1, E2-S2, E3-S1 — projects, competitor lists, run lifecycle with mock data (done)
- **Sprint 3:** E3-S2, E4-S1, E4-S2 — real Apify scraping, Claude summaries, full pipeline (done)
- **Sprint 4:** E5-S1, E5-S2, E6-S1 — results table, XLSX export, shortlist (done)
- **Sprint 5:** E6-S2, E7-S1, E7-S2 — history, usage rollups, admin view → **usable MVP** (E7-S2 carried into Sprint 6)
- **Sprint 6:** hardening + cost + redesign + **Telegram test launch, no payments** (see above)
- **Sprint 7 (proposed, 2026-07-21 reprioritization — single-blogger MVP focus):** E8-S6 Telegram Mini App bootstrap fix (critical, live-blocking bug for the pilot — root cause fixed, pending real-device smoke test, see BACKLOG.md), E5-S4 subscriber count in results table, E2-S3 competitor profile enrichment (depends on E5-S4's `fetch_profile`), E5-S3 comments count column, E5-S5 virality score per publication (depends on E5-S4)
- **Sprint 8 (locked, 2026-07-22 execution plan):** E13-S1/S2/S3 (nav restructure: Детали/Результаты/Анализ, Details dashboard, Competitors trim), E16-S1 (Analysis teaser), E15-S1/S2/S3 (run detail: AI summary, top-5-by-virality, Summary+Publications tabs)
- **Sprint 9 (locked, 2026-07-22 execution plan):** E14-S1..S5 — scheduled runs (schema, CRUD + arq cron dispatcher, Scheduled Runs page, Run-now/Schedule wiring, Telegram notification)
- **Sprint 10 (locked, 2026-07-22 execution plan, D30):** E8-S3 re-scoped — single 1990₽/mo → 2000-token subscription via Telegram Stars
- **Post-MVP (not yet ordered):** E3-S3/E3-S4 (run resume, two-phase cost confirmation), E3-S5 HikerAPI switch, E7-S3 pre-public-launch hardening, E8-S4 share-to-bot, E9 Public API, E10 Content Generation, E11 IG Connection/Publishing/Analytics (spike first) — see BACKLOG.md and docs/ARCHITECTURE.md § Roadmap beyond MVP
