# TESTING — content-scout

## Principles
- Every story ships tests covering its acceptance criteria (part of DoD).
- CI never calls paid external services — Apify and Anthropic are always mocked or replayed from recorded fixtures.
- One manual smoke test per story on DEV (defined in the story, <2 min).

## Layers

### Backend unit/service (pytest)
- Services in isolation: url_normalizer, metrics, estimator, summarizer (mocked Anthropic), xlsx_export.
- Fixtures: factory helpers per model; `backend/tests/fixtures/apify_ig_sample.json` — a recorded real Apify payload used by the mock platform and integration tests.

### Backend API (pytest + httpx AsyncClient)
- Per-endpoint tests against a real Postgres test DB (transaction-rollback per test).
- Always test: happy path, validation failure (Russian error message present), auth required, cross-tenant access → 404.

### Worker/pipeline
- `test_pipeline.py`: full run against the mock platform + mocked Claude — asserts status transitions, content_items written, usage_events written, partial-failure behavior (one failing account doesn't fail the run), idempotent re-summarization.

### Frontend
- MVP gate: `tsc --noEmit` + eslint in CI.
- Component tests (vitest + testing-library) added when a component carries real logic (results table sorting state, run progress polling).

### Smoke on DEV (manual, per story)
- Defined in each story's "Smoke test" section; performed before marking done.

## What we deliberately don't test in MVP
- Live Apify actor behavior (validated manually in E3-S2's smoke test; actor payload drift is caught by re-recording the fixture).
- Load/perf — pilot scale (D11).
