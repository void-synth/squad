#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if ! command -v pg_isready >/dev/null 2>&1; then
  echo "pg_isready not found. Install PostgreSQL client tools or start Postgres manually."
  exit 1
fi

if ! pg_isready -h localhost -p 5432 >/dev/null 2>&1; then
  echo "PostgreSQL does not appear to be running on localhost:5432"
  exit 1
fi

if ! command -v redis-cli >/dev/null 2>&1; then
  echo "redis-cli not found. Ensure Redis is running on localhost:6379"
  exit 1
fi

if ! redis-cli -u "${REDIS_URL:-redis://localhost:6379}" ping >/dev/null 2>&1; then
  echo "Redis does not appear to be running (redis ping failed)."
  exit 1
fi

if [ -d "venv" ]; then
  # shellcheck disable=SC1091
  source "venv/bin/activate"
fi

if [ ! -f ".env" ]; then
  cp .env.example .env
  echo "Created .env from .env.example — fill in SQUAD_* keys before demo."
fi

echo -e "\033[32mTitan backend is running at http://localhost:8000\033[0m"
exec uvicorn main:app --reload --port 8000
