# Vitality AI Coach for Garmin

Self-hostable AI health & fitness coach that reads Garmin Connect data and
answers questions about training, sleep, stress, recovery and body battery.

This file is read automatically by AI coding agents (Claude Code, Codex,
opencode). If a user asks you to "set this repo up", follow the steps below.

## Structure

```
.
├── src/                  # FastAPI backend (Python)
│   ├── main.py           # App entry, SPA serving, rate limits
│   ├── api/              # Routes: auth, chat, sync, insights, background_sync, setup
│   ├── agents/           # LLM agents: fitness_coach, health_analyst, orchestrator
│   ├── db/               # SQLAlchemy models + migrations/
│   ├── garmin/           # Garmin Connect client
│   ├── services/         # context, data_sync, insights, tts, firebase, scheduler
│   └── config.py         # Settings from env vars + runtime config overlay
├── frontend/             # React SPA (Vite + TypeScript + Tailwind 4)
├── scripts/              # check-secrets.sh (secret scan before publishing)
├── tests/                # Backend tests (pytest)
├── Dockerfile            # Multi-stage build (frontend + API)
├── compose.yaml          # One-command self-hosting (prebuilt image)
├── compose.build.yaml    # Build from source (dev / pre-release)
└── start.sh              # One-command installer
```

## Quickstart

Requirements: Python 3.11+, Node 20+.

```bash
git clone https://github.com/ArtemKx1/vitality-ai-coach-public.git
cd vitality-ai-coach-public

# Backend (prefer uv if available: `uv sync`)
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

cp .env.example .env

# Frontend — build once; the backend serves it at :8000
cd frontend
npm install
npm run build          # VITE_BASE=/ (self-host at the root)
cd ..

# Run — SQLite DB auto-initializes; first-run wizard shows in the browser
uvicorn src.main:app --host 0.0.0.0 --port 8000
```

## Verify it works

- `GET /health` responds `{"status":"ok"}`.
- `GET /api/v1/setup/status` responds `{"setup_required": true, ...}` on first run.
- The user opens http://localhost:8000 and completes the browser wizard:
  AI provider → account (optional Garmin Connect login) → start chatting.

## Configuration

- Settings come from env vars (see `.env.example`) and can be overridden at
  runtime by the setup wizard, which writes `data/config.json`.
- `LLM_PROVIDER`: `ollama`, `groq`, `openrouter`, `openai`,
  `openai_compatible`, `mistral`, or `auto`. Free tiers work (e.g. Groq).
- `DATABASE_URL` defaults to a local SQLite file; use a Postgres URL for
  multi-user hosting.
- `APP_SECRET_KEY` is auto-generated on first boot (persisted to
  `data/.secret`) — **do not regenerate it afterwards**; it encrypts Garmin
  credentials and chat messages.
- Optional features (push notifications, text-to-speech, social login) degrade
  gracefully when not configured.

## Rules

- **NEVER** commit `.env`, `.env.*` (except `.env.example`), or anything under `data/`.
- **NEVER** regenerate `APP_SECRET_KEY` — it encrypts user data.
- Verify the backend with `python3 -m pytest tests/ -q`.
- Run `./scripts/check-secrets.sh` before publishing a release.
- Setup endpoints (`/api/v1/setup/*`) return 403 once the first account exists.
