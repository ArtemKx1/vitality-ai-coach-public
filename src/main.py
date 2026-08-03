from __future__ import annotations

import logging
import os
from pathlib import Path

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded
from fastapi.responses import JSONResponse

from src.rate_limit import limiter

from src.api.auth import router as auth_router
from src.api.routes import router
from src.api.background_sync import router as background_sync_router
from src.api.setup import router as setup_router
from src.config import load_runtime_overrides, settings
from src.db.models import init_db
from src.services.firebase import init_firebase

logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)

IS_DEV = os.environ.get("ENV", "dev") != "production"


load_runtime_overrides()
init_db()
logger.info("Database initialized")
init_firebase()

app = FastAPI(title="Garmin AI Coach", version="0.1.0")

# Rate limiting
app.state.limiter = limiter

MAX_BODY_SIZE = 1 * 1024 * 1024  # 1 MB

@app.middleware("http")
async def limit_body_size(request: Request, call_next):
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > MAX_BODY_SIZE:
                return JSONResponse(status_code=413, content={"detail": "Request body too large"})
        except ValueError:
            return JSONResponse(status_code=400, content={"detail": "Invalid content-length header"})
    return await call_next(request)

@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request, exc):
    return JSONResponse(
        status_code=429,
        content={"detail": "Too many requests. Please try again later."},
    )

# CORS — explicit origins in production
allowed_origins = [
    origin.strip()
    for origin in settings.allowed_origins.split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/v1")
app.include_router(router, prefix="/api/v1")
app.include_router(background_sync_router, prefix="/api/v1")
app.include_router(setup_router, prefix="/api/v1")


@app.get("/health")
def health():
    return {"status": "ok"}


frontend_dist = Path("frontend/dist")
frontend_base = settings.frontend_base.rstrip("/")


def _serve_or_index(full_path: str, index_html: str) -> FileResponse | HTMLResponse:
    """Serve a real built file (favicon, logo, ...) if it exists, else the SPA shell."""
    if full_path:
        candidate = (frontend_dist / full_path).resolve()
        if str(candidate).startswith(str(frontend_dist.resolve())) and candidate.is_file():
            return FileResponse(candidate)
    return HTMLResponse(index_html)


if frontend_dist.exists():
    app.mount(
        f"{frontend_base}/assets",
        StaticFiles(directory=str(frontend_dist / "assets")),
        name="frontend_assets",
    )

    index_html = (frontend_dist / "index.html").read_text()

    if frontend_base:
        @app.get(f"{frontend_base}/{{full_path:path}}")
        async def serve_frontend(full_path: str):
            return _serve_or_index(full_path, index_html)

        @app.get(frontend_base)
        async def serve_frontend_root():
            return HTMLResponse(index_html)

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """SPA fallback — serve real files (favicons, logo) or index.html for deep links."""
        return _serve_or_index(full_path, index_html)
else:
    app.mount("/static", StaticFiles(directory="static"), name="static")

    @app.get("/")
    def index():
        with open("static/index.html") as f:
            return HTMLResponse(f.read())


if __name__ == "__main__":
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=IS_DEV)
