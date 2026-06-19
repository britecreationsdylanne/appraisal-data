from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import chat, export, factfinder, meta, reports, saved, trends
from .config import get_settings

settings = get_settings()
app = FastAPI(title="Appraisal Data Research API", version="0.1.0")

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
    # Create new tables + lightweight column migrations + refresh seed templates,
    # all without touching existing rows.
    from sqlalchemy import text

    from .db import Base, SessionLocal, engine
    from . import models  # noqa: F401
    from .templates_seed import seed_templates

    Base.metadata.create_all(engine)
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE chat_logs ADD COLUMN IF NOT EXISTS owner VARCHAR(120) DEFAULT 'local'"))
        conn.execute(text("ALTER TABLE chat_logs ADD COLUMN IF NOT EXISTS shared BOOLEAN DEFAULT false"))
        conn.execute(text("ALTER TABLE saved_templates ADD COLUMN IF NOT EXISTS owner VARCHAR(120) DEFAULT 'system'"))
        conn.execute(text("ALTER TABLE saved_templates ADD COLUMN IF NOT EXISTS shared BOOLEAN DEFAULT false"))
        conn.execute(text("ALTER TABLE report_runs ADD COLUMN IF NOT EXISTS owner VARCHAR(120) DEFAULT 'local'"))
        conn.execute(text("ALTER TABLE report_runs ADD COLUMN IF NOT EXISTS shared BOOLEAN DEFAULT false"))
        conn.execute(text("UPDATE saved_templates SET owner='system', shared=true WHERE is_seed = true"))
        # Indexes for the columns we filter/group on most (cheap on synthetic data;
        # essential once the real table is large).
        for ddl in (
            "CREATE INDEX IF NOT EXISTS ix_appr_source_year ON appraisals (largest_diamond_source, appraisal_year)",
            "CREATE INDEX IF NOT EXISTS ix_appr_cat_year ON appraisals (briteco_category, appraisal_year)",
            "CREATE INDEX IF NOT EXISTS ix_appr_color_clarity ON appraisals (color_band, clarity_band)",
            "CREATE INDEX IF NOT EXISTS ix_appr_shape ON appraisals (shape)",
            "CREATE INDEX IF NOT EXISTS ix_appr_quarter ON appraisals (year_quarter)",
        ):
            conn.execute(text(ddl))
    with SessionLocal() as s:
        seed_templates(s)
        s.commit()
    # Populate synthetic watches once (non-destructive — skips if already seeded).
    from .seed.generate import seed_watches_if_empty

    seed_watches_if_empty()


@app.get("/api/health")
def health():
    return {"ok": True, "souls_live": settings.souls_live}
