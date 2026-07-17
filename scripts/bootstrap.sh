#!/usr/bin/env bash
# Local environment setup for content-scout. Idempotent.
set -euo pipefail
cd "$(dirname "$0")/.."

echo "==> Checking prerequisites"
command -v docker >/dev/null || { echo "docker required"; exit 1; }
command -v python3.12 >/dev/null || command -v python3 >/dev/null || { echo "python 3.12 required"; exit 1; }
command -v node >/dev/null || { echo "node 22+ required"; exit 1; }

echo "==> Starting Postgres + Redis"
docker compose up -d

echo "==> Backend venv + deps"
[ -d backend/.venv ] || python3 -m venv backend/.venv
backend/.venv/bin/pip install -q -r backend/requirements.txt

echo "==> Frontend deps"
(cd frontend && npm install)

[ -f .env ] || { cp .env.example .env; echo "==> Created .env from template — fill in secrets (see ENV.md)"; }

echo "==> Running migrations (skipped if alembic not yet initialized)"
[ -d backend/alembic ] && (cd backend && .venv/bin/alembic upgrade head) || true

cat <<'EOF'

Done. To run:
  backend: cd backend && .venv/bin/uvicorn src.main:app --reload
  worker:  cd backend && .venv/bin/arq src.worker.WorkerSettings
  web:     cd frontend && npm run dev
EOF
