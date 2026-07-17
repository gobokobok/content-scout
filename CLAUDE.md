# CLAUDE.md — content-scout session bootstrap

## Session startup protocol

Read in this order, every session:
1. This file
2. `SPRINT.md` — current sprint and active story
3. The active story's entry in `SPRINT.md` / `BACKLOG.md`
4. `DONE.md` — what was recently completed and handovers
5. `CONVENTIONS.md` — coding standards

## Project summary

content-scout is a SaaS where a user creates a project, adds up to 50 competitor Instagram accounts, and runs an analysis over a chosen window (≤7 days). The system scrapes published content via Apify, computes engagement metrics, generates 1–2 sentence Claude summaries (caption + cover image), and presents a sortable, XLSX-exportable table; users promote winners to a shortlist and can review run/shortlist history. Every run is metered in a usage ledger (Apify units + Claude tokens) so token-based billing can be added later; UI is Russian-only via next-intl.

## Environments and deploy triggers

| Env | URL | Trigger |
|---|---|---|
| local | http://localhost:3000 (web) / :8000 (api) | manual |
| DEV | https://web-dev-99e3.up.railway.app / https://api-dev-8d6e.up.railway.app | push to `main` |
| PROD | https://web-production-1bd7f0.up.railway.app / https://api-production-b1b5.up.railway.app | git tag `v*` |

Railway project: https://railway.com/project/a5fbb916-354f-47db-ab91-c3bdc5c236f6 (envs: `dev`, `production`; services: api, worker, web + Postgres, Redis per env). GitHub: https://github.com/gobokobok/content-scout

## Key docs

- `docs/ARCHITECTURE.md` — system design, data model, run lifecycle
- `docs/TECH_STACK.md` — stack choices and rationale
- `docs/TESTING.md` — test strategy per layer
- `docs/UI_GUIDELINES.md` — Russian UI, layout, table UX
- `docs/PROMPTS.md` — Claude prompts (summaries, future scripts)
- `DECISIONS.md` — every binding decision; read before proposing alternatives
- `ENV.md` — all environment variables

## Current sprint and active story

- **Sprint:** 1
- **Active story:** E1-S1 (see `SPRINT.md`)

## Hard constraints

- No new dependencies without a `DECISIONS.md` entry.
- All UI strings go through next-intl; no hardcoded user-facing text. Russian is the only locale for MVP.
- Every screen must be usable at 375px width (D16): mobile-first Tailwind, no fixed-width layouts; wide tables scroll horizontally inside their own container, never the page.
- Every external cost (Apify results, Claude tokens) must be recorded as a `usage_events` row at the moment it is incurred — never retrofitted.
- Platform-specific scraping/metrics code lives behind the `Platform` interface (`backend/src/platforms/`); nothing outside it may import Apify directly.
- IG photo posts/carousels have no public view counts — views columns render "—", never 0, for those types.
- Analysis runs execute in the worker, never in a request handler.
- Do not touch billing/payments — out of scope until a DECISIONS.md entry says otherwise.
- Read only the files listed in the active story; ask before reading beyond them.
