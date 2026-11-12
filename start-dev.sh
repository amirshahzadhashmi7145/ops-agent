#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

if ! docker info >/dev/null 2>&1; then
  echo "Docker is not running. Start Docker Desktop / 'sudo systemctl start docker', then retry."
  exit 1
fi

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Created .env from .env.example — set OPENAI_API_KEY before chatting."
fi

echo "Starting Ops Agent (UI :3001 · API :8001 · DB :5433)..."
docker compose up --build "$@"
