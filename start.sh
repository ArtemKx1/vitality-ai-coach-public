#!/usr/bin/env bash
# Vitality AI Coach for Garmin — one-command self-host.
#
#   curl -fsSL https://raw.githubusercontent.com/ArtemKx1/vitality-ai-coach-public/main/start.sh -o start.sh
#   bash start.sh
#
# Downloads the compose files (if missing), copies .env.example → .env (if missing),
# starts the app (prebuilt GHCR image, falling back to building from source),
# then opens http://localhost:8000 where the setup wizard lives.
set -euo pipefail

REPO_RAW="${GARMIN_COACH_RAW:-https://raw.githubusercontent.com/ArtemKx1/vitality-ai-coach-public/main}"
PORT="${PORT:-8000}"

say() { printf '\033[1;36m▶\033[0m %s\n' "$*"; }
die() { printf '\033[1;31m✗\033[0m %s\n' "$*" >&2; exit 1; }

command -v docker >/dev/null 2>&1 || die "Docker is not installed. Install it from https://www.docker.com/products/docker-desktop/ and run this script again."
docker info >/dev/null 2>&1 || die "Docker is installed but not running. Start Docker Desktop (or the docker daemon) and run this script again."

cd "$(dirname "$0")"

for f in compose.yaml compose.build.yaml .env.example; do
  if [ ! -f "$f" ]; then
    say "Downloading $f…"
    curl -fsSL "$REPO_RAW/$f" -o "$f" || die "Could not download $f from $REPO_RAW"
  fi
done

if [ ! -f .env ]; then
  say "No .env found — creating one from .env.example (the app runs fine with defaults; set an LLM key to unlock chat)."
  cp .env.example .env
fi

mkdir -p data

if docker compose pull --quiet 2>/dev/null && docker compose config --quiet 2>/dev/null; then
  say "Starting from the prebuilt image…"
  docker compose up -d || die "Failed to start with the prebuilt image. Try: GARMIN_COACH_RAW=… bash start.sh"
else
  say "No prebuilt image yet — building from source (first build takes a few minutes)…"
  docker compose -f compose.build.yaml up -d --build || die "Build failed. See the output above."
fi

sleep 2
say "App is running at http://localhost:$PORT — complete the setup wizard in your browser."

case "$(uname -s)" in
  Darwin)  open "http://localhost:$PORT" ;;
  Linux)   command -v xdg-open >/dev/null 2>&1 && xdg-open "http://localhost:$PORT" || true ;;
  *)       true ;;
esac
