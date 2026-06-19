from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import SavedItem
from .chat import current_user

router = APIRouter(prefix="/api/saved", tags=["saved"])


class SavedIn(BaseModel):
    kind: str            # "trend" | "image"
    title: str
    summary: str = ""
    payload: dict = {}
    shared: bool = False


class ShareIn(BaseModel):
    shared: bool


def _row(r: SavedItem) -> dict:
    return {"id": r.id, "kind": r.kind, "owner": r.owner, "shared": r.shared,
            "title": r.title, "summary": r.summary, "payload": r.payload,
            "created_at": str(r.created_at)}


def save_item(db: Session, kind: str, owner: str, title: str, summary: str, payload: dict) -> SavedItem:
    item = SavedItem(kind=kind, owner=owner, title=title, summary=summary, payload=payload)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("")
def list_saved(kind: str | None = None, db: Session = Depends(get_db), user: str = Depends(current_user)):
    q = select(SavedItem).where(SavedItem.owner == user)
    if kind:
        q = q.where(SavedItem.kind == kind)
    rows = db.execute(q.order_by(SavedItem.created_at.desc()).limit(200)).scalars().all()
    return [_row(r) for r in rows]


@router.get("/library")
def library(kind: str | None = None, db: Session = Depends(get_db)):
    q = select(SavedItem).where(SavedItem.shared.is_(True))
    if kind:
        q = q.where(SavedItem.kind == kind)
    rows = db.execute(q.order_by(SavedItem.created_at.desc()).limit(200)).scalars().all()
    return [_row(r) for r in rows]


@router.post("")
def create(body: SavedIn, db: Session = Depends(get_db), user: str = Depends(current_user)):
    item = SavedItem(kind=body.kind, owner=user, shared=body.shared, title=body.title,
                     summary=body.summary, payload=body.payload)
    db.add(item)
    db.commit()
    db.refresh(item)
    return _row(item)


@router.post("/{sid}/share")
def share(sid: int, body: ShareIn, db: Session = Depends(get_db), user: str = Depends(current_user)):
    r = db.get(SavedItem, sid)
    if not r:
        raise HTTPException(404, "Not found")
    if r.owner != user:
        raise HTTPException(403, "You can only share your own items")
    r.shared = body.shared
    db.commit()
    return _row(r)


@router.delete("/{sid}")
def delete(sid: int, db: Session = Depends(get_db), user: str = Depends(current_user)):
    r = db.get(SavedItem, sid)
    if not r:
        raise HTTPException(404, "Not found")
    if r.owner != user:
        raise HTTPException(403, "You can only delete your own items")
    db.delete(r)
    db.commit()
    return {"ok": True}
