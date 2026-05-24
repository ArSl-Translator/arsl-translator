#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-$HOME/arsl-translator}"
BRANCH="${BRANCH:-main}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"
ENV_FILE="${ENV_FILE:-.env.production}"

cd "$APP_DIR"

if [ -f karsl_runtime_bundle.tgz ] && ! git ls-files --error-unmatch karsl_runtime_bundle.tgz >/dev/null 2>&1; then
  mv karsl_runtime_bundle.tgz "$HOME/karsl_runtime_bundle.tgz.$(date +%Y%m%d%H%M%S).backup"
fi

git fetch origin "$BRANCH"
git checkout "$BRANCH"
git pull --ff-only origin "$BRANCH"

if [ ! -f "$ENV_FILE" ]; then
  echo "Missing $ENV_FILE. Copy .env.production.example and fill production secrets first." >&2
  exit 1
fi

if docker compose version >/dev/null 2>&1; then
  COMPOSE=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE=(docker-compose)
else
  echo "Docker Compose is not installed. Install Docker Compose v2 or docker-compose." >&2
  exit 1
fi

"${COMPOSE[@]}" -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d --build --remove-orphans
"${COMPOSE[@]}" -f "$COMPOSE_FILE" --env-file "$ENV_FILE" ps
