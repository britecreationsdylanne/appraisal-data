from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..agents import souls
from ..db import get_db
from ..semantic.loader import attribute_menu, dimensions, metrics

router = APIRouter(prefix="/api/meta", tags=["meta"])


@router.get("")
def meta(db: Session = Depends(get_db)):
    row = db.execute(text("SELECT MIN(appraisal_date) AS lo, MAX(appraisal_date) AS hi, "
                          "COUNT(*) AS n FROM appraisals")).one()
    lo = row.lo or date(2019, 1, 1)
    hi = row.hi or date.today()
    return {
        "date_bounds": {"min": str(lo), "max": str(hi)},
        "row_count": int(row.n),
        "granularities": ["day", "month", "quarter", "year"],
        "metrics": [{"key": k, "label": v["label"], "format": v.get("format")}
                    for k, v in metrics().items()],
        "attributes": attribute_menu(),
        "baselines": dimensions().get("baselines", {}),
        "souls_live": souls.LIVE,
    }
