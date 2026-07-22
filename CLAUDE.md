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

## Priority: Telegram Mini App (mobile) first — 2026-07-22

The Telegram Mini App is the primary delivery target and needs to ship ASAP; the desktop/browser experience is secondary. Concretely:
- Prefer work that moves the mobile miniapp forward. If a task is purely about the browser/desktop surface (desktop-only polish, desktop keyboard/mouse interactions, browser-specific verification) and it would cost meaningful time, **delay it** rather than doing it now — leave a note (in the story's Handover, or here) instead of spending the session on it.
- Don't sink time fighting browser-only test-harness/dev-server quirks (e.g. scratch-preview click-through races) when the underlying change isn't miniapp-specific — note the gap as deferred and move on; this has already cost real time in this project (see DONE.md's "Results/Details landing-page swap" entry, 2026-07-22).
- Mobile-first constraints below (375px usable, cards not tables) already point the UI at this target — this note is about where to spend *dev/test time*, not a new UI rule.

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

- **Sprint:** 9 complete (E14 scheduled runs — schema/migration, CRUD API + arq cron dispatcher, Scheduled Runs page, Run-now/Schedule choice, Telegram notification — all shipped 2026-07-22, see SPRINT.md). Sprints 1–8 also complete. **Sprint 10 (E8-S3 monetization, D30) is next up and no longer blocked.** DEV smoke tests across Sprints 6–9 are still deferred pending a real-device pass (26 outstanding as of Sprint 9's close — consider a dedicated integration/smoke-test story before Sprint 10 ships to production).

## Hard constraints

- No new dependencies without a `DECISIONS.md` entry.
- All UI strings go through next-intl; no hardcoded user-facing text. Russian is the only locale for MVP.
- Every screen must be usable at 375px width (D16): mobile-first Tailwind, no fixed-width layouts. From E12-S2 on: tables become cards below 768px; until then wide tables scroll horizontally inside their own container, never the page.
- Light theme only (D28): no `dark:` classes; all colors via the design tokens in `globals.css`; icons via lucide-react, never emoji.
- Every external cost (Apify results, Claude tokens) must be recorded as a `usage_events` row at the moment it is incurred — never retrofitted.
- Platform-specific scraping/metrics code lives behind the `Platform` interface (`backend/src/platforms/`); nothing outside it may import Apify directly.
- IG photo posts/carousels have no public view counts — views columns render "—", never 0, for those types.
- Analysis runs execute in the worker, never in a request handler.
- Do not touch billing/payments — out of scope until a DECISIONS.md entry says otherwise.
- Read only the files listed in the active story; ask before reading beyond them.
