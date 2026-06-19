from fastapi import APIRouter
from pydantic import BaseModel

from ..services import factfinder

router = APIRouter(prefix="/api/factfinder", tags=["factfinder"])


class FactFinderRequest(BaseModel):
    text: str


@router.post("/analyze")
def analyze(req: FactFinderRequest):
    return factfinder.analyze(req.text)
