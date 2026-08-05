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

- **Sprint:** 9 complete (E14 scheduled runs — schema/migration, CRUD API + arq cron dispatcher, Scheduled Runs page, Run-now/Schedule choice, Telegram notification — all shipped 2026-07-22, see SPRINT.md). Sprints 1–8 also complete. **E17 (Run Deep Analysis, all 9 stories) shipped 2026-07-25, out of order, per direct user request** — comment scraping (dual-vendor, D32), Haiku extraction + Sonnet synthesis (D33), the Разбор запуска history/report UI, thin-coverage degrade + partial refund. **E18 (Run-Centric Navigation & Redesign, 5 stories) shipped 2026-07-26→28, also out of order and backfilled into BACKLOG.md/DONE.md only at the 2026-07-28 `/sprint-review`** — unified cross-project run feed + FAB (supersedes E13's tab bar), rebuilt run-creation/schedule cards, deep-analysis auto-chain failure visibility, Usage page reworked around Balance. **Sprint 10 complete 2026-07-31** — E8-S3 (Telegram Stars token top-ups, D37) shipped 2026-07-29; E19-S1 did *not* close (carried over, see below). Two unplanned items also landed and were backfilled at the 2026-07-31 `/sprint-review`: **E17-S10** (deep-analysis job-cancellation bug fix — a stuck-forever `extracting` row, root-caused to `asyncio.CancelledError` bypassing `except Exception` on arq's job-timeout cancellation) and **E8-S8** (2026-07-30 Mini App iOS 401-recovery + auto-project-creation hotfix, D38). **Sprint 11 complete 2026-08-04** — E19-S1 (DEV smoke-test sweep) closed 2026-07-31; E20-S2 (worker/DB capacity, D46) and E20-S3 (rate limiting & provider-quota guardrails, D47) closed 2026-08-03. Unplanned items backfilled at the 2026-08-04 `/sprint-review`: **E21-S1** (Standalone Analysis pipeline scoping, D40/D41/D42/D43, no code), **E2-S4** (competitor deletion/picker bugfixes), **E17-S11** (deep-analysis pipeline hardening — synthesis truncation, root-logger visibility, timeout headroom, notification timing, and **D48**'s usage-based token-charging redesign). Sprint 12, re-ordered 2026-08-04 via PBR for an ASAP paying-customer launch. **E21-S2 (standalone Analysis pipeline) shipped 2026-08-04, delivered end-to-end in one session per direct user request** — own scraping (account or single-post mode), incremental token charging (D50), plus three further rounds of fixes driven by the user's own DEV smoke test (synthesis thin-data bug, a `/me/usage` double-line bug, a real comments-charged-vs-analyzed overcharge, and UX polish); promoted a real Apify Free Plan account limitation to new story **E20-S5** (comment-count ceiling, blocks re-enabling some shipped-but-disabled UI options). **Active: E3-S8** (run-estimate messaging) next, then E15-S5 (bumped to high — run details modal), E18-S6 (notification drawer fix), E22-S1 (new epic E22 — Review Telegram completion message rework, per user-supplied target format), then the prior order resumes: E19-S3 (DEV smoke sweep, in-progress, paused mid-way by user choice), E20-S1 (batch deep-analysis comment scraping), E8-S7 (token-purchase ledger visibility). Not scheduled: E20-S4 (50→20 competitor cap, pending product decision) and the Analysis-side/report-page half of the PBR's notification-messaging item — still needs concrete detail from the user before more E22 stories open, see SPRINT.md.** Sprint 12's declared order is now fully shipped except **E19-S3** (DEV smoke sweep, still in-progress, paused mid-way by user choice — the only open item). Four more untracked fixes landed post-close, 2026-08-04→05, and were backfilled at the 2026-08-05 `/sprint-review`: **E17-S12** (deep-analysis synthesis retry on malformed tool_use), **E21-S4** (post-mode Analysis account hiding), **E21-S5** (D51 — synthesis priced at real Sonnet rates + base per-run token charge), and **E22-S2**/**E3-S9** (overarching Telegram-notify toggle + pinned-post last-N fix, one commit split across two stories by feature area; also diagnosed but did not resolve a PROD Telegram-silence report — root cause unconfirmed, see BACKLOG.md's `[E22-S2]` Handover). A recurring-bug cluster across the Analysis pipeline (E17-S12/E21-S4/E21-S5, three real bugs within ~36 hours of E21-S2 shipping) was flagged at this review with a proposed **E21-S6** hardening story, not yet added to BACKLOG.md pending the user's go-ahead. **Active: E19-S3** (resume when the user is ready), next-sprint planning otherwise still open.**

## Story-tracking discipline (added 2026-07-28 `/sprint-review`)

Before implementing a non-trivial UI/backend change requested directly in chat (not via `/start-story`), check whether it maps to an existing BACKLOG.md story. If it doesn't:
- Open one via `/add-story` first, **or**
- If the user wants to proceed immediately without that ceremony, that's fine — but explicitly flag at the end of that session that the work is untracked and needs a `/sprint-review` backfill, so it gets documented within days, not after a whole redesign has piled up undocumented (see E18's backfill note in SPRINT.md/DONE.md for what happens when this doesn't happen — 26 commits, 3 days, zero story IDs, discovered only at the next review).

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
- Do not verify UI/frontend changes yourself — no Browser tool, no scratch-preview routes, no screenshots. The user runs their own smoke-test pass before anything ships and has said this verification step was costing too much time/resources. For frontend changes, lint/typecheck (`tsc`, `eslint`) is sufficient; skip visual verification unless the user explicitly asks you to check something in the browser.
