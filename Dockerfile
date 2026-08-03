# Multi-stage build
#   Stage 1: build the React SPA
#   Stage 2: Python API serving the SPA + /api/v1
#
# Build args:
#   VITE_BASE      — SPA base path (default "/", i.e. self-host at the site root).
#   VITE_SITE_URL  — public origin used for canonical/OG tags (optional for self-host).

# ── Stage 1: frontend ─────────────────────────────────────────────────────────
FROM node:22-alpine AS frontend-build
WORKDIR /app/frontend

ARG VITE_BASE=/
ARG VITE_SITE_URL=
ENV VITE_BASE=$VITE_BASE
ENV VITE_SITE_URL=$VITE_SITE_URL
ENV PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

# ── Stage 2: backend ──────────────────────────────────────────────────────────
FROM python:3.12-slim

RUN useradd -m -u 1001 appuser

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir .

COPY src/ ./src/
COPY --from=frontend-build /app/frontend/dist ./frontend/dist

RUN chown -R appuser:appuser /app

ENV PORT=8080
ENV FRONTEND_BASE=/

EXPOSE $PORT

USER appuser

CMD ["sh", "-c", "exec uvicorn src.main:app --host 0.0.0.0 --port $PORT"]
