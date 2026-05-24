#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-$HOME/arsl-translator}"
REPO_URL="${REPO_URL:-https://github.com/ArSl-Translator/arsl-translator.git}"
BRANCH="${BRANCH:-main}"

sudo apt-get update
sudo apt-get install -y ca-certificates curl git docker.io

sudo systemctl enable --now docker
sudo usermod -aG docker "$USER"

if ! docker compose version >/dev/null 2>&1 && ! command -v docker-compose >/dev/null 2>&1; then
  mkdir -p "$HOME/.docker/cli-plugins"
  arch="$(uname -m)"
  case "$arch" in
    x86_64) compose_arch="x86_64" ;;
    aarch64|arm64) compose_arch="aarch64" ;;
    *) echo "Unsupported architecture for Docker Compose: $arch" >&2; exit 1 ;;
  esac
  curl -SL "https://github.com/docker/compose/releases/download/v2.32.4/docker-compose-linux-${compose_arch}" \
    -o "$HOME/.docker/cli-plugins/docker-compose"
  chmod +x "$HOME/.docker/cli-plugins/docker-compose"
fi

if [ ! -d "$APP_DIR/.git" ]; then
  git clone --branch "$BRANCH" "$REPO_URL" "$APP_DIR"
else
  if [ -f "$APP_DIR/karsl_runtime_bundle.tgz" ] && ! git -C "$APP_DIR" ls-files --error-unmatch karsl_runtime_bundle.tgz >/dev/null 2>&1; then
    mv "$APP_DIR/karsl_runtime_bundle.tgz" "$HOME/karsl_runtime_bundle.tgz.$(date +%Y%m%d%H%M%S).backup"
  fi
  git -C "$APP_DIR" fetch origin "$BRANCH"
  git -C "$APP_DIR" checkout "$BRANCH"
  git -C "$APP_DIR" pull --ff-only origin "$BRANCH"
fi

mkdir -p "$APP_DIR/models" "$APP_DIR/outputs/index" "$APP_DIR/data" "$APP_DIR/artifacts"

if [ ! -f "$APP_DIR/.env.production" ]; then
  cp "$APP_DIR/.env.production.example" "$APP_DIR/.env.production"
  chmod 600 "$APP_DIR/.env.production"
  echo "Created $APP_DIR/.env.production. Edit it before running deploy/deploy.sh."
fi

echo "Bootstrap complete."
echo "Important: log out and back in, or run 'newgrp docker', so your user can run Docker without sudo."
