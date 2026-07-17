# content-scout

SaaS for competitor content analysis on Instagram (YouTube/TikTok/Threads later). A user creates a project, adds up to 50 competitor IG accounts, runs an analysis over a chosen window (≤7 days), and gets a sortable, Excel-exportable table of everything published in that window — engagement metrics plus 1–2 sentence AI summaries. Winners get promoted to a shortlist; later, video scripts are generated from shortlisted items. UI is in Russian.

## Stack

- **Backend:** Python 3.12, FastAPI, SQLAlchemy + Alembic, arq worker, PostgreSQL, Redis
- **Frontend:** Next.js 15, TypeScript, Tailwind, TanStack Table, next-intl (ru)
- **Data:** Apify Instagram scrapers
- **AI:** Claude Haiku 4.5 (summaries), stronger Claude model for future script generation
- **Deploy:** Railway (DEV + PROD), GitHub Actions

## Repository layout

```
backend/    FastAPI app, worker, migrations, backend tests
frontend/   Next.js app
docs/       Architecture, tech stack, testing, UI, prompts
scripts/    bootstrap.sh (local setup), promote.sh (dev → prod)
```

## Environments

| Env | What | Deploy trigger |
|---|---|---|
| local | docker-compose Postgres + Redis, uvicorn + next dev | manual |
| DEV | Railway | push to `main` |
| PROD | Railway | git tag `v*` |

## Setup (local)

```bash
./scripts/bootstrap.sh
cp .env.example .env   # fill in values (see ENV.md)
```

## Working on this project

This project uses the APEX-DEV methodology. Start every session by reading `CLAUDE.md`, then `SPRINT.md`. Start a story with `/start-story E1-S1`.
