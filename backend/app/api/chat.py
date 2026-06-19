from datetime import date

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import ChatLog
from ..services import chat

router = APIRouter(prefix="/api/chat", tags=["chat"])


def current_user(x_user: str | None = Header(default=None)) -> str:
    """Lightweight identity until real auth lands: the frontend sends X-User."""
    return (x_user or "local").strip() or "local"


class ChatRequest(BaseModel):
    question: str
    date_start: date
    date_end: date


class ShareRequest(BaseModel):
    shared: bool


def _row(r: ChatLog) -> dict:
    return {"id": r.id, "owner": r.owner, "shared": r.shared, "question": r.question,
            "answer": r.answer, "n": r.n, "confidence": r.confidence, "caveat": r.caveat,
            "date_start": str(r.date_start), "date_end": str(r.date_end),
            "created_at": str(r.created_at)}


@router.post("")
def ask(req: ChatRequest, db: Session = Depends(get_db), user: str = Depends(current_user)):
    return chat.ask(db, req.question, req.date_start, req.date_end, user=user)


@router.get("/history")
def history(db: Session = Depends(get_db), user: str = Depends(current_user)):
    """The current user's private saved questions."""
    rows = db.execute(
        select(ChatLog).where(ChatLog.owner == user).order_by(ChatLog.created_at.desc()).limit(100)
    ).scalars().all()
    return [_row(r) for r in rows]


@router.get("/library")
def library(db: Session = Depends(get_db)):
    """Shared library — questions anyone has chosen to share with the team."""
    rows = db.execute(
        select(ChatLog).where(ChatLog.shared.is_(True)).order_by(ChatLog.created_at.desc()).limit(200)
    ).scalars().all()
    return [_row(r) for r in rows]


@router.post("/{cid}/share")
def share(cid: int, body: ShareRequest, db: Session = Depends(get_db), user: str = Depends(current_user)):
    r = db.get(ChatLog, cid)
    if not r:
        raise HTTPException(404, "Not found")
    if r.owner != user:
        raise HTTPException(403, "You can only share your own questions")
    r.shared = body.shared
    db.commit()
    return _row(r)


@router.delete("/history")
def clear_history(db: Session = Depends(get_db), user: str = Depends(current_user)):
    """Clear only the current user's private (unshared) questions."""
    db.query(ChatLog).filter(ChatLog.owner == user, ChatLog.shared.is_(False)).delete()
    db.commit()
    return {"ok": True}


@router.delete("/{cid}")
def delete_one(cid: int, db: Session = Depends(get_db), user: str = Depends(current_user)):
    r = db.get(ChatLog, cid)
    if not r:
        raise HTTPException(404, "Not found")
    if r.owner != user:
        raise HTTPException(403, "You can only delete your own questions")
    db.delete(r)
    db.commit()
    return {"ok": True}
