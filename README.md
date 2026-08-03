<div align="center">

<img src="assets/screenshot.png" alt="Vitality AI Coach" width="100%" />

# <img src="assets/garmin-logo.png" alt="Garmin" width="140" align="middle" /> Vitality AI Coach for Garmin

<p>
  <em>Self-hostable AI health & fitness coach — reads your <strong>Garmin Connect</strong> data and
  answers questions about training, sleep, stress, recovery and body battery.</em>
</p>

<p>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-green" alt="MIT License" /></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-3.11+-blue" alt="Python 3.11+" /></a>
  <a href="https://nodejs.org/"><img src="https://img.shields.io/badge/Node.js-20+-orange" alt="Node 20+" /></a>
  <a href="https://www.docker.com/"><img src="https://img.shields.io/badge/Docker-Compose-2496ED" alt="Docker Compose" /></a>
  <a href="#hosted-deployment"><img src="https://img.shields.io/badge/Container-GHCR-000?logo=docker" alt="GHCR" /></a>
  <a href="#install-with-ai-agents"><img src="https://img.shields.io/badge/🤖%20Install-Claude%20%7C%20Codex%20%7C%20opencode-4f46e5" alt="Install via AI agents" /></a>
  <a href="https://github.com/ArtemKx1/vitality-ai-coach-public/stargazers"><img src="https://img.shields.io/github/stars/ArtemKx1/vitality-ai-coach-public?style=social" alt="GitHub stars" /></a>
</p>

**100% self-hosted** &nbsp;·&nbsp; **bring your own model** &nbsp;·&nbsp; **zero-config wizard** &nbsp;·&nbsp; **no telemetry**

<sub><a href="#features">✨ Features</a> · <a href="#install-with-ai-agents">🤖 AI Agents</a> · <a href="#one-command-docker">🚀 Docker</a> · <a href="#install-locally">📦 Local</a> · <a href="#configuration">⚙️ Config</a> · <a href="#local-model-ollama">🦙 Ollama</a> · <a href="#development">🛠 Dev</a> · <a href="#hosted-deployment">☁️ Hosted</a> · <a href="#privacy--security">🔒 Privacy</a> · <a href="#faq">❓ FAQ</a> · <a href="#license">📄 License</a></sub>

</div>

<p align="center">
  💜 <strong>Enjoying Vitality AI Coach?</strong> Support the project — every tip is appreciated:<br/><br/>
  <a href="https://ko-fi.com/artemkuprin"><img src="https://img.shields.io/badge/☕%20Buy%20me%20a%20coffee-ko--fi.com%2Fartemkuprin-FF5E5B" alt="Buy me a coffee on Ko-fi" /></a>
</p>

---

<h2 id="features">✨ Features</h2>

- **🔒 100% self-hosted** — your Garmin credentials and chat history stay on your
  machine (encrypted with `APP_SECRET_KEY`). Only the LLM provider you pick
  ever sees your data.
- **🧠 Bring your own model** — Groq, OpenRouter, OpenAI, Mistral, any
  OpenAI-compatible endpoint, or **local Ollama** (fully offline).
- **🪄 Zero-config setup** — first-run wizard in the browser: connect AI → create
  your account → connect Garmin → start chatting. No terminal gymnastics.
- **📈 Data you actually care about** — sleep, HRV, training load, stress,
  recovery and body battery, explained in your own language.

---

<h2 id="install-with-ai-agents">🤖 Install with AI agents</h2>

Clone the repo, then let **Claude Code**, **Codex** or **opencode** do the rest —
they read [`AGENTS.md`](AGENTS.md) automatically:

```bash
git clone https://github.com/ArtemKx1/vitality-ai-coach-public.git
cd vitality-ai-coach-public
```

| Agent | Command |
|---|---|
| **Claude Code** | `claude "Set up this repo and verify it runs locally"` |
| **Codex** (OpenAI) | `codex "Set up this repo and verify it runs locally"` |
| **opencode** | `opencode "Set up this repo and verify it runs locally"` |

No CLI installed, or pasting into a chat? Copy this block into any AI agent
(ChatGPT, Claude, Gemini…) with the repo already cloned:

```text
Set up Vitality AI Coach for Garmin locally and verify it runs.

1. Backend: create a Python venv, install deps (`pip install -e ".[dev]"`),
   and copy `.env.example` → `.env`.
2. LLM: set an LLM_PROVIDER with a working key. Prefer Groq (free tier, no
   credit card); if you have no key, leave it and tell me to use the browser
   wizard or local Ollama instead.
3. Frontend: `cd frontend && npm install && npm run build` (VITE_BASE=/).
4. Start the server: `uvicorn src.main:app --host 0.0.0.0 --port 8000`.
5. Verify: `GET /health` returns ok, and `GET /api/v1/setup/status` returns
   `{"setup_required": true, ...}`.
6. Tell me to open http://localhost:8000 for the first-run wizard.

Rules: never commit `.env`; never touch `data/`; never regenerate
APP_SECRET_KEY if one already exists.
```

---

<h2 id="one-command-docker">🚀 One-command install (Docker)</h2>

**Requirements:** Docker with Compose v2.

```bash
curl -fsSL https://raw.githubusercontent.com/ArtemKx1/vitality-ai-coach-public/main/start.sh -o start.sh
bash start.sh
```

The script detects Docker, downloads the compose files, creates `.env` if
needed, and starts the app — pulling the prebuilt image from GHCR, or building
from source if the image isn't available yet. Then it opens
**http://localhost:8000**.

Manual equivalent (builds from source):

```bash
cp .env.example .env          # defaults are fine — the wizard handles the rest
docker compose -f compose.build.yaml up -d --build
open http://localhost:8000
```

---

<h2 id="install-locally">📦 Install locally</h2>

**Requirements:** Python 3.11+ and Node 20+. A Garmin account. One LLM API key
(free tiers work — e.g. Groq) or local Ollama.

```bash
git clone https://github.com/ArtemKx1/vitality-ai-coach-public.git
cd vitality-ai-coach-public

# Backend (Python)
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

cp .env.example .env

# Frontend (React SPA) — build once; the backend serves it at :8000
cd frontend
npm install
npm run build          # VITE_BASE=/ (self-host at the root)
cd ..

# Run — SQLite DB auto-initializes, the first-run wizard shows in the browser
uvicorn src.main:app --host 0.0.0.0 --port 8000
```

Open **http://localhost:8000** — you'll be taken to the setup wizard. It walks
you through:

1. **AI provider** — pick Groq/OpenRouter/OpenAI/Mistral/Ollama, paste a key
   (or nothing for Ollama).
2. **Your account** — email/password + optional Garmin Connect login.
3. **Done** — chat about your sleep, HRV, training load and more.

> Using `uv`? Then `uv sync` replaces the venv + pip steps.

---

<h2 id="configuration">⚙️ Configuration</h2>

All settings come from environment variables (`.env`) or the setup wizard
(which writes `data/config.json`). Key ones:

| Variable | Default | Purpose |
|---|---|---|
| `LLM_PROVIDER` | `auto` | `ollama`, `groq`, `openrouter`, `openai`, `openai_compatible`, `mistral`, `auto` |
| `GROQ_API_KEY` / `OPENROUTER_API_KEY` / `OPENAI_API_KEY` / `MISTRAL_API_KEY` | — | keys for cloud providers (free tiers available) |
| `OLLAMA_HOST` / `OLLAMA_MODEL` | `http://localhost:11434` | local LLM (fully offline) |
| `DATABASE_URL` | `sqlite:///./data/garmin_coach.db` | SQLite by default; use Postgres for multi-user hosting |
| `APP_SECRET_KEY` | auto-generated | **encrypts** Garmin credentials + chat messages; never regenerate it |
| `SCHEDULER_ENABLED` | `true` | built-in background sync (set `false` if you use external cron) |

See `.env.example` for the full list. Optional features (push notifications,
text-to-speech, social login) degrade gracefully when not configured.

---

<h2 id="local-model-ollama">🦙 Using a local model (Ollama)</h2>

```bash
ollama pull gemma4:e4b          # or any model you like
docker compose -f compose.build.yaml up -d --build
# set LLM_PROVIDER=ollama, OLLAMA_HOST=http://ollama:11434 in .env
```

Fully offline: nothing leaves your machine.

---

<h2 id="development">🛠 Development</h2>

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
uvicorn src.main:app --reload --port 8000          # API

cd frontend && npm install && npm run dev           # SPA (Vite dev server)
```

Backend tests: `python3 -m pytest tests/ -q`. Pre-publish secret scan:
`./scripts/check-secrets.sh`.

---

<h2 id="building-the-image-yourself">🐳 Building the image yourself</h2>

```bash
docker build -t vitality-ai-coach .
docker run -p 8000:8000 -v "$PWD/data:/app/data" vitality-ai-coach
```

---

<h2 id="hosted-deployment">☁️ Hosted deployment</h2>

A prebuilt image is published to GHCR (`ghcr.io/artemkx1/vitality-ai-coach-public`).
Run it directly:

```bash
docker run -d --name vitality-ai-coach -p 8000:8000 \
  -v "$PWD/data:/app/data" \
  ghcr.io/artemkx1/vitality-ai-coach-public:latest
```

Set secrets (`APP_SECRET_KEY`, `DATABASE_URL`, LLM keys) via environment
variables or a `.env` file — never in git. For multiple instances, disable the
in-process scheduler and trigger `/api/v1/internal/sync-all-active` from an
external cron.

---

<h2 id="privacy--security">🔒 Privacy &amp; security</h2>

- Garmin credentials and chat history are Fernet-encrypted at rest.
- `APP_SECRET_KEY` is generated on first boot (stored in `data/.secret`).
  Back it up — losing it makes stored data unrecoverable.
- This app only ever talks to: your LLM provider, Garmin Connect (to sync your
  data), and the services you explicitly configure. **No telemetry.**

---

<h2 id="faq">❓ FAQ</h2>

<details>
<summary>📱 <b>Which Garmin watches are supported?</b></summary>

Any Garmin watch that syncs to **Garmin Connect** works — there is no device
whitelist. Insights get richer with the metrics your watch records:

- **Modern watches** (Venu, Vivoactive, Forerunner, Fenix/Epix, Instinct 2+)
  feed the full stack: HRV, Body Battery, stress, SpO2, sleep stages, training
  effect and VO2max.
- **Basic trackers** (e.g. Vivosmart) provide steps, heart rate and sleep
  basics.

Fewer metrics just means fewer charts — the app still works on any Garmin.
</details>

<details>
<summary>🔒 <b>Does this phone home?</b></summary>

Only to the services you configure: your LLM provider and Garmin Connect (to
sync your data). No telemetry.
</details>

<details>
<summary>🔑 <b>What happens to my Garmin password?</b></summary>

It is encrypted with `APP_SECRET_KEY` and sent only to Garmin Connect when
syncing. Chat history is encrypted too.
</details>

<details>
<summary>🧠 <b>Which LLM models work?</b></summary>

Any OpenAI-compatible chat model — Groq, OpenRouter, OpenAI, Mistral, or any
custom endpoint. Local Ollama is fully free and private.
</details>

<details>
<summary>⏱ <b>How often is my Garmin data synced?</b></summary>

The built-in scheduler pulls your latest Garmin data in the background, so chat
answers stay fresh without manual resyncs. For multi-instance setups, disable
it (`SCHEDULER_ENABLED=false`) and trigger
`/api/v1/internal/sync-all-active` from an external cron instead.
</details>

<details>
<summary>💾 <b>Where is my data stored?</b></summary>

Locally, in a SQLite database under `data/` (or any `DATABASE_URL` you set,
e.g. Postgres). Garmin credentials and chat messages are Fernet-encrypted at
rest.
</details>

<details>
<summary>❄️ <b>Can I run it fully offline?</b></summary>

Yes. Point `LLM_PROVIDER=ollama` at a local Ollama instance and nothing ever
leaves your machine — no cloud LLM, no Garmin credential outside your box
(except Garmin Connect when it syncs).
</details>

<details>
<summary>🪄 <b>The wizard is gone / shows 403?</b></summary>

Setup is only available before the first account is created. Change settings via
environment variables afterwards.
</details>

<details>
<summary>🤖 <b>Can an AI agent install it for me?</b></summary>

Yes — see [Install with AI agents](#install-with-ai-agents). Claude Code, Codex
and opencode read `AGENTS.md` automatically.
</details>

---

<h2 id="project-layout">📁 Project layout</h2>

```
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

---

<h2 id="license">📄 License</h2>

[MIT](LICENSE)
