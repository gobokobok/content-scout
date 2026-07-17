# SPRINT.md — content-scout

## Sprint 1 — Walking skeleton

**Goal:** A deployed, authenticated, Russian-language shell: anyone can register on DEV, log in, and see their empty workspace. Schema and CI foundations in place for everything that follows.

**Stories (in order):**

| Story | Title | Status |
|---|---|---|
| E1-S1 | Monorepo scaffold, local env, CI, DEV deploy | ready |
| E1-S2 | Database schema and migrations | ready |
| E1-S3 | Email+password auth and personal workspace | ready |

**Active story:** E1-S1 — start with `/start-story E1-S1`

Full story definitions live in `BACKLOG.md`.

## Sprint plan (projection, adjust at each /sprint-review)

- **Sprint 2:** E2-S1, E2-S2, E3-S1 — projects, competitor lists, run lifecycle with mock data
- **Sprint 3:** E3-S2, E4-S1, E4-S2 — real Apify scraping, Claude summaries, full pipeline
- **Sprint 4:** E5-S1, E5-S2, E6-S1 — results table, XLSX export, shortlist
- **Sprint 5:** E6-S2, E7-S1, E7-S2 — history, usage rollups, admin view → **usable MVP**
- **Sprint 6+ (post-MVP, not yet ordered):** E8 Telegram Integration & Monetization (Login → notifications → Mini App + Stars), E9 Public API & Engine Integration — see BACKLOG.md and docs/ARCHITECTURE.md § Roadmap beyond MVP
