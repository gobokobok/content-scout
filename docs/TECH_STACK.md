# TECH_STACK — content-scout

| Layer | Choice | Version | Rationale |
|---|---|---|---|
| Language (backend) | Python | 3.12 | Best ecosystem for scraping/LLM pipelines; user's standard |
| API framework | FastAPI | latest | Async, typed, Pydantic validation |
| ORM / migrations | SQLAlchemy 2.0 (async) + Alembic | latest | Standard, migration discipline |
| Job queue | arq | latest | Lightweight async worker over Redis; Celery is overkill at pilot scale |
| Queue broker | Redis 7 | Railway plugin | One-click on Railway |
| Database | PostgreSQL 16 | Railway plugin | Relational domain; JSONB for raw scrape payloads |
| Scraping | Apify (IG actors) | apify-client | D2 — pay-per-result, managed anti-bot |
| AI | Anthropic SDK | latest | D7 — `claude-haiku-4-5-20251001` for summaries (multimodal: caption + cover image); stronger Claude model for post-MVP scripts |
| XLSX export | openpyxl | latest | D9 — streams .xlsx with hyperlinks |
| Auth | passlib[bcrypt] + PyJWT | latest | Email+password → JWT (D4) |
| Language (frontend) | TypeScript | 5.x | — |
| Frontend framework | Next.js (App Router) | 15 | — |
| UI | Tailwind CSS | 4 | Fast, consistent |
| Tables | TanStack Table | 8 | Sorting/pagination for the results grid |
| i18n | next-intl | latest | D8 — ru-only, i18n-ready |
| Lint/format | ruff + mypy (be), eslint + prettier (fe) | latest | — |
| Tests | pytest + pytest-asyncio | latest | External services mocked in CI |
| CI/CD | GitHub Actions | — | test on PR/push; DEV deploy on main; PROD on tag |
| Hosting | Railway | — | DEV + PROD environments; services: api, worker, web + Postgres, Redis |

## Cost model (pilot scale, per analysis run)

Worst case 50 accounts × 7 days, ~10 items/account average → ~500 items:
- Apify posts scraper: ~$1.5–3.0 per 1k results → **~$0.75–1.50/run**
- Haiku summaries (caption + 1 image ≈ 1.3k input / 60 output tokens per item) → **~$0.10–0.20/run**
- Typical pilot run (10 accounts, 3 days): **well under $0.50**

The estimator (E3-S1) uses these unit costs from config; confirm dialog shows the number before spend (D10).
