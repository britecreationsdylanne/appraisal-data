from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..db import get_db
from ..services import trends
from .chat import current_user
from .saved import save_item

router = APIRouter(prefix="/api/trends", tags=["trends"])


class TrendRequest(BaseModel):
    dimension: str
    value: str
    date_start: date
    date_end: date
    granularity: str = "year"
    save: bool = True


@router.post("")
def run(req: TrendRequest, db: Session = Depends(get_db), user: str = Depends(current_user)):
    try:
        res = trends.run_trends(db, req.dimension, req.value, req.date_start,
                                req.date_end, req.granularity)
    except KeyError as e:
        raise HTTPException(status_code=400, detail=f"Unknown attribute: {e}")

    if req.save and not res.get("placeholder"):
        item = save_item(
            db, kind="trend", owner=user,
            title=f"{res['dimension_label']} = {res['value']}",
            summary=res.get("summary", ""),
            payload={"dimension": req.dimension, "value": req.value,
                     "granularity": req.granularity,
                     "date_start": str(req.date_start), "date_end": str(req.date_end)},
        )
        res["saved_id"] = item.id
    return res
