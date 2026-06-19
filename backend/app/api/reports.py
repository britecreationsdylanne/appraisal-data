from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import ReportRun, SavedTemplate
from ..services import analyze, reports
from .chat import current_user

router = APIRouter(prefix="/api", tags=["reports"])


class TemplateIn(BaseModel):
    name: str
    description: str = ""
    spec: dict


class TemplatePatch(BaseModel):
    name: str | None = None
    description: str | None = None
    spec: dict | None = None


class ShareIn(BaseModel):
    shared: bool


class RunIn(BaseModel):
    date_start: date
    date_end: date
    granularity: str = "quarter"
    save: bool = True


class PreviewIn(BaseModel):
    spec: dict
    date_start: date
    date_end: date
    granularity: str = "quarter"


def _tpl_dict(t: SavedTemplate) -> dict:
    # bucket: "official" (locked seed) | "mine" | "shared"
    return {"id": t.id, "name": t.name, "description": t.description, "is_seed": t.is_seed,
            "owner": t.owner, "shared": t.shared, "spec": t.spec, "created_at": str(t.created_at)}


# ---- templates -----------------------------------------------------------
@router.get("/templates")
def list_templates(db: Session = Depends(get_db)):
    rows = db.execute(select(SavedTemplate).order_by(SavedTemplate.is_seed.desc(),
                                                     SavedTemplate.name)).scalars().all()
    return [_tpl_dict(t) for t in rows]


@router.post("/templates")
def create_template(body: TemplateIn, db: Session = Depends(get_db), user: str = Depends(current_user)):
    t = SavedTemplate(name=body.name, description=body.description, spec=body.spec,
                      is_seed=False, owner=user, shared=False)
    db.add(t)
    db.commit()
    db.refresh(t)
    return _tpl_dict(t)


@router.get("/templates/{tid}")
def get_template(tid: int, db: Session = Depends(get_db)):
    t = db.get(SavedTemplate, tid)
    if not t:
        raise HTTPException(404, "Template not found")
    return _tpl_dict(t)


@router.patch("/templates/{tid}")
def update_template(tid: int, body: TemplatePatch, db: Session = Depends(get_db),
                    user: str = Depends(current_user)):
    t = db.get(SavedTemplate, tid)
    if not t:
        raise HTTPException(404, "Template not found")
    # Official (seed) templates are locked: editing one creates a copy you own,
    # leaving the shared original intact.
    if t.is_seed:
        copy = SavedTemplate(
            name=body.name or f"{t.name} (my copy)",
            description=body.description if body.description is not None else t.description,
            spec=body.spec if body.spec is not None else t.spec,
            is_seed=False, owner=user, shared=False,
        )
        db.add(copy)
        db.commit()
        db.refresh(copy)
        return _tpl_dict(copy)
    if t.owner != user:
        raise HTTPException(403, "You can only edit your own reports")
    if body.name is not None:
        t.name = body.name
    if body.description is not None:
        t.description = body.description
    if body.spec is not None:
        t.spec = body.spec
    db.commit()
    db.refresh(t)
    return _tpl_dict(t)


@router.post("/templates/{tid}/share")
def share_template(tid: int, body: ShareIn, db: Session = Depends(get_db),
                   user: str = Depends(current_user)):
    t = db.get(SavedTemplate, tid)
    if not t:
        raise HTTPException(404, "Template not found")
    if t.is_seed:
        raise HTTPException(400, "Official templates are already shared")
    if t.owner != user:
        raise HTTPException(403, "You can only share your own reports")
    t.shared = body.shared
    db.commit()
    db.refresh(t)
    return _tpl_dict(t)


@router.post("/templates/{tid}/duplicate")
def duplicate_template(tid: int, db: Session = Depends(get_db), user: str = Depends(current_user)):
    t = db.get(SavedTemplate, tid)
    if not t:
        raise HTTPException(404, "Template not found")
    copy = SavedTemplate(name=f"{t.name} (copy)", description=t.description, spec=t.spec,
                         is_seed=False, owner=user, shared=False)
    db.add(copy)
    db.commit()
    db.refresh(copy)
    return _tpl_dict(copy)


@router.delete("/templates/{tid}")
def delete_template(tid: int, db: Session = Depends(get_db), user: str = Depends(current_user)):
    t = db.get(SavedTemplate, tid)
    if not t:
        raise HTTPException(404, "Template not found")
    if t.is_seed:
        raise HTTPException(400, "Official templates cannot be deleted")
    if t.owner != user:
        raise HTTPException(403, "You can only delete your own reports")
    db.delete(t)
    db.commit()
    return {"ok": True}


# ---- preview (unsaved) ---------------------------------------------------
@router.post("/reports/preview")
def preview(body: PreviewIn, db: Session = Depends(get_db)):
    return reports.run_report(db, body.spec, body.date_start, body.date_end, body.granularity)


# ---- run a template (re-runnable with new dates) -------------------------
@router.post("/templates/{tid}/run")
def run_template(tid: int, body: RunIn, db: Session = Depends(get_db), user: str = Depends(current_user)):
    t = db.get(SavedTemplate, tid)
    if not t:
        raise HTTPException(404, "Template not found")
    fact_pack = reports.run_report(db, t.spec, body.date_start, body.date_end, body.granularity)
    run_id = None
    if body.save:
        run = ReportRun(template_id=t.id, template_name=t.name, owner=user,
                        date_start=body.date_start, date_end=body.date_end,
                        granularity=body.granularity, fact_pack=fact_pack)
        db.add(run)
        db.commit()
        db.refresh(run)
        run_id = run.id
    return {"template_id": t.id, "run_id": run_id, "fact_pack": fact_pack}


# ---- run history (per user) ---------------------------------------------
def _run_row(r: ReportRun) -> dict:
    return {"id": r.id, "template_id": r.template_id, "template_name": r.template_name,
            "owner": r.owner, "shared": r.shared, "date_start": str(r.date_start),
            "date_end": str(r.date_end), "granularity": r.granularity, "analyzed": r.analyzed,
            "n_total": r.fact_pack.get("n_total"), "run_at": str(r.run_at)}


@router.get("/runs")
def list_runs(db: Session = Depends(get_db), user: str = Depends(current_user)):
    rows = db.execute(
        select(ReportRun).where(ReportRun.owner == user).order_by(ReportRun.run_at.desc())
    ).scalars().all()
    return [_run_row(r) for r in rows]


@router.get("/runs/library")
def runs_library(db: Session = Depends(get_db)):
    rows = db.execute(
        select(ReportRun).where(ReportRun.shared.is_(True)).order_by(ReportRun.run_at.desc())
    ).scalars().all()
    return [_run_row(r) for r in rows]


@router.get("/runs/{rid}")
def get_run(rid: int, db: Session = Depends(get_db)):
    r = db.get(ReportRun, rid)
    if not r:
        raise HTTPException(404, "Run not found")
    return {"id": r.id, "template_id": r.template_id, "template_name": r.template_name,
            "owner": r.owner, "shared": r.shared, "date_start": str(r.date_start),
            "date_end": str(r.date_end), "granularity": r.granularity, "analyzed": r.analyzed,
            "fact_pack": r.fact_pack, "analysis": r.analysis, "run_at": str(r.run_at)}


@router.post("/runs/{rid}/share")
def share_run(rid: int, body: ShareIn, db: Session = Depends(get_db), user: str = Depends(current_user)):
    r = db.get(ReportRun, rid)
    if not r:
        raise HTTPException(404, "Run not found")
    if r.owner != user:
        raise HTTPException(403, "You can only share your own runs")
    r.shared = body.shared
    db.commit()
    return _run_row(r)


@router.delete("/runs/{rid}")
def delete_run(rid: int, db: Session = Depends(get_db), user: str = Depends(current_user)):
    r = db.get(ReportRun, rid)
    if not r:
        raise HTTPException(404, "Run not found")
    if r.owner != user:
        raise HTTPException(403, "You can only delete your own runs")
    db.delete(r)
    db.commit()
    return {"ok": True}


# ---- analyze (run the souls) --------------------------------------------
@router.post("/runs/{rid}/analyze")
def analyze_run(rid: int, db: Session = Depends(get_db)):
    r = db.get(ReportRun, rid)
    if not r:
        raise HTTPException(404, "Run not found")
    result = analyze.analyze_fact_pack(r.fact_pack)
    r.analysis = result
    r.analyzed = True
    db.commit()
    return result
