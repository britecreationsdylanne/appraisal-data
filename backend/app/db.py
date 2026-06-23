from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from .config import get_settings

settings = get_settings()

# --- Two databases ---------------------------------------------------------
# Appraisal DB: the real appraisal data. READ-ONLY in production.
appraisal_engine = create_engine(settings.database_url, pool_pre_ping=True, future=True)

# App DB: the tool's own read/write data (saved templates, history, saved items).
# A separate instance in production; falls back to the appraisal/local DB when
# APP_DATABASE_URL is unset (local dev — one DB for everything).
app_engine = create_engine(settings.app_database_url or settings.database_url,
                           pool_pre_ping=True, future=True)

# Separate declarative bases so we can route each group to the right engine and
# only ever create/seed the appraisal tables locally.
AppraisalBase = declarative_base()   # Appraisal, Watch  (read-only in prod)
AppBase = declarative_base()         # SavedTemplate, ReportRun, ChatLog, SavedItem

# One Session, routed per-table:
#   * raw SQL (db.execute(text(...))) + AppraisalBase models -> appraisal_engine (default)
#   * AppBase models -> app_engine (matched via the class MRO)
# So every analytics SELECT hits the read-only appraisal DB, while the app's own
# writes land in the writable app DB — with no changes at the call sites.
SessionLocal = sessionmaker(
    bind=appraisal_engine,
    binds={AppBase: app_engine},
    autoflush=False,
    autocommit=False,
    future=True,
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
