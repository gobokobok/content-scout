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
| 2 | E7-S4 | Pilot security guardrails (critical) | pending |
| 3 | E4-S3 | Claude cost optimization | pending |
| 4 | E12-S1 | Design system re-skin (light theme v1) | pending |
| 5 | E12-S2 | Mobile cards, bottom navigation, UX states | pending |
| 6 | E8-S1 | Telegram Login | pending |
| 7 | E8-S5 | Telegram Mini App shell (no billing) — **sprint exit criterion** | pending |
| 8 | E8-S2 | Telegram bot notifications (stretch — skip if the sprint runs long) | pending |

**Sprint exit check:** open the DEV bot from a phone, tap «Открыть content-scout», run the full flow inside Telegram, and share the bot handle with a second account.

## Sprint plan (projection, adjust at each /sprint-review)

- **Sprint 2:** E2-S1, E2-S2, E3-S1 — projects, competitor lists, run lifecycle with mock data (done)
- **Sprint 3:** E3-S2, E4-S1, E4-S2 — real Apify scraping, Claude summaries, full pipeline (done)
- **Sprint 4:** E5-S1, E5-S2, E6-S1 — results table, XLSX export, shortlist (done)
- **Sprint 5:** E6-S2, E7-S1, E7-S2 — history, usage rollups, admin view → **usable MVP** (E7-S2 carried into Sprint 6)
- **Sprint 6:** hardening + cost + redesign + **Telegram test launch, no payments** (see above)
- **Sprint 7+ (not yet ordered):** E8-S3 Telegram Stars subscriptions + D26 token billing, E8-S4 share-to-bot, E3-S3/E3-S4 (run resume, two-phase cost confirmation), E7-S3 pre-public-launch hardening, E9 Public API, E10 Content Generation, E11 IG Connection/Publishing/Analytics (spike first) — see BACKLOG.md and docs/ARCHITECTURE.md § Roadmap beyond MVP
