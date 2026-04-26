from contextlib import asynccontextmanager
import logging
import os
import traceback
from pathlib import Path
from typing import Optional

import uvicorn
from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from backend.db.database import engine, AsyncSession, get_db
from backend.modules.vk import router as vk_router
from backend.modules.llm import router as llm_router
from backend.modules.profiles import router as profiles_router
from backend.modules.condition import router as condition_router
from backend.modules.dzen import router as dzen_router
from backend.modules.sheet_parser import router as sheet_parser_router
from backend.modules.report import router as report_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await engine.dispose()


app = FastAPI(
    title="Bezumny MAX",
    description="Platforma dlya analitiki",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS: localhost + LAN-адреса (192.168 / 10 / 172.16-31)
# + временные домены туннелей (cloudflared / ngrok).
CORS_ALLOW_REGEX = (
    r"^https?://("
    r"localhost(:\d+)?"
    r"|127\.0\.0\.1(:\d+)?"
    r"|192\.168\.\d{1,3}\.\d{1,3}(:\d+)?"
    r"|10\.\d{1,3}\.\d{1,3}\.\d{1,3}(:\d+)?"
    r"|172\.(1[6-9]|2[0-9]|3[0-1])\.\d{1,3}\.\d{1,3}(:\d+)?"
    r"|[A-Za-z0-9-]+\.trycloudflare\.com"
    r"|[A-Za-z0-9-]+\.ngrok(-free)?\.(app|io)"
    r")$"
)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=CORS_ALLOW_REGEX,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    tb = traceback.format_exc()
    logger.error("Unhandled exception on %s %s:\n%s", request.method, request.url, tb)
    return JSONResponse(status_code=500, content={"detail": str(exc), "traceback": tb})


app.include_router(vk_router)
app.include_router(llm_router)
app.include_router(profiles_router)
app.include_router(condition_router)
app.include_router(dzen_router)
app.include_router(sheet_parser_router)
app.include_router(report_router)


@app.get("/health/db")
async def health_db(db: AsyncSession = Depends(get_db)):
    result = await db.execute(text("SELECT 1"))
    return {"status": "ok", "db_response": result.scalar()}


# ---------- Раздача собранного фронта (опционально, prod-режим) ----------
def _resolve_frontend_dist() -> Optional[Path]:
    env_dir = os.getenv("FRONTEND_DIST")
    if env_dir:
        candidate = Path(env_dir).expanduser().resolve()
        return candidate if candidate.is_dir() else None
    repo_root = Path(__file__).resolve().parents[2]
    candidate = repo_root.parent / "Pro-Techno" / "dist"
    return candidate if candidate.is_dir() else None


_FRONTEND_DIST = _resolve_frontend_dist()

if _FRONTEND_DIST is not None:
    logger.info("Serving frontend from %s", _FRONTEND_DIST)
    _assets_dir = _FRONTEND_DIST / "assets"
    if _assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=_assets_dir), name="frontend-assets")

    @app.get("/", include_in_schema=False)
    async def root_index():
        return FileResponse(_FRONTEND_DIST / "index.html")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str):
        target = (_FRONTEND_DIST / full_path).resolve()
        if _FRONTEND_DIST in target.parents and target.is_file():
            return FileResponse(target)
        return FileResponse(_FRONTEND_DIST / "index.html")
else:
    @app.get("/")
    async def root():
        return {"message": "Backend is running"}


if __name__ == "__main__":
    host = os.getenv("BACKEND_HOST", "0.0.0.0")
    port = int(os.getenv("BACKEND_PORT", "8000"))
    reload_flag = os.getenv("BACKEND_RELOAD", "true").lower() in {"1", "true", "yes"}
    uvicorn.run("backend.app.main:app", host=host, port=port, reload=reload_flag)
