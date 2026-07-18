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
| E5-S2 | XLSX export | backlog |
| E6-S1 | Shortlist | backlog |

## Sprint plan (projection, adjust at each /sprint-review)

- **Sprint 2:** E2-S1, E2-S2, E3-S1 — projects, competitor lists, run lifecycle with mock data (done)
- **Sprint 3:** E3-S2, E4-S1, E4-S2 — real Apify scraping, Claude summaries, full pipeline (done)
- **Sprint 4:** E5-S1, E5-S2, E6-S1 — results table, XLSX export, shortlist
- **Sprint 5:** E6-S2, E7-S1, E7-S2 — history, usage rollups, admin view → **usable MVP**
- **Sprint 6+ (post-MVP, not yet ordered):** E8 Telegram Integration & Monetization (Login → notifications → Mini App + Stars → share-to-bot), E9 Public API & Engine Integration, E10 Content Generation (scripts → assets → review), E11 IG Connection, Publishing & Analytics (spike first) — see BACKLOG.md and docs/ARCHITECTURE.md § Roadmap beyond MVP
