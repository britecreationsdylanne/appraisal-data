from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from .api import chat, export, factfinder, meta, reports, saved, trends
from .config import get_settings

settings = get_settings()
app = FastAPI(title="Appraisal Data Research API", version="0.1.0")

# CORS only matters for local dev (Vite on :5176 → API on :8010). In production the
# backend serves the built frontend from the same origin, so no cross-origin calls.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5176", "http://127.0.0.1:5176"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(meta.router)
app.include_router(chat.router)
app.include_router(trends.router)
app.include_router(reports.router)
app.include_router(export.router)
app.include_router(saved.router)
app.include_router(factfinder.router)


@app.on_event("startup")
def _ensure_tables():
    from sqlalchemy import text

    from .db import AppBase, AppraisalBase, SessionLocal, app_engine, appraisal_engine
    from . import models  # noqa: F401
    from .templates_seed import seed_templates

    # --- App DB (read/write) — ALWAYS. Owns templates, history, saved items. ---
    AppBase.metadata.create_all(app_engine)
    with app_engine.begin() as conn:
        conn.execute(text("ALTER TABLE chat_logs ADD COLUMN IF NOT EXISTS owner VARCHAR(120) DEFAULT 'local'"))
        conn.execute(text("ALTER TABLE chat_logs ADD COLUMN IF NOT EXISTS shared BOOLEAN DEFAULT false"))
        conn.execute(text("ALTER TABLE saved_templates ADD COLUMN IF NOT EXISTS owner VARCHAR(120) DEFAULT 'system'"))
        conn.execute(text("ALTER TABLE saved_templates ADD COLUMN IF NOT EXISTS shared BOOLEAN DEFAULT false"))
        conn.execute(text("ALTER TABLE report_runs ADD COLUMN IF NOT EXISTS owner VARCHAR(120) DEFAULT 'local'"))
        conn.execute(text("ALTER TABLE report_runs ADD COLUMN IF NOT EXISTS shared BOOLEAN DEFAULT false"))
        conn.execute(text("UPDATE saved_templates SET owner='system', shared=true WHERE is_seed = true"))
    with SessionLocal() as s:
        seed_templates(s)
        s.commit()

    # --- Appraisal DB — LOCAL/dev ONLY. In production this is the real,
    #     READ-ONLY appraisal database; we never create/seed/alter it. ---
    if settings.is_local:
        AppraisalBase.metadata.create_all(appraisal_engine)
        with appraisal_engine.begin() as conn:
            for ddl in (
                "CREATE INDEX IF NOT EXISTS ix_appr_source_year ON appraisals (largest_diamond_source, appraisal_year)",
                "CREATE INDEX IF NOT EXISTS ix_appr_cat_year ON appraisals (briteco_category, appraisal_year)",
                "CREATE INDEX IF NOT EXISTS ix_appr_color_clarity ON appraisals (color_band, clarity_band)",
                "CREATE INDEX IF NOT EXISTS ix_appr_shape ON appraisals (shape)",
                "CREATE INDEX IF NOT EXISTS ix_appr_quarter ON appraisals (year_quarter)",
            ):
                conn.execute(text(ddl))
        from .seed.generate import seed_watches_if_empty

        seed_watches_if_empty()


@app.get("/api/health")
def health():
    return {"ok": True, "souls_live": settings.souls_live, "env": settings.app_env}


# --- Serve the built frontend (production single-container). In dev this folder
#     doesn't exist and Vite serves the UI instead. ---
_STATIC = Path(__file__).resolve().parent.parent / "static"
if _STATIC.exists():
    app.mount("/", StaticFiles(directory=str(_STATIC), html=True), name="spa")

    @app.exception_handler(StarletteHTTPException)
    async def _spa_fallback(request: Request, exc: StarletteHTTPException):
        # Deep links (e.g. /reports) that aren't real files fall back to the SPA;
        # genuine API 404s still return JSON.
        if exc.status_code == 404 and not request.url.path.startswith("/api"):
            return FileResponse(_STATIC / "index.html")
        return await http_exception_handler(request, exc)
