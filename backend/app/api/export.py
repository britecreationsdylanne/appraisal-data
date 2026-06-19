from fastapi import APIRouter
from pydantic import BaseModel

from ..agents import souls
from ..services import export_edit, export_svg

router = APIRouter(prefix="/api/export", tags=["export"])


class ExportRequest(BaseModel):
    spec: dict  # {title, subtitle, footer, kind: bar|line|stats, labels, series, stats, background, accent}
    size: str = "ig_square"


class EditRequest(BaseModel):
    spec: dict
    instruction: str
    size: str = "ig_square"


@router.get("/sizes")
def sizes():
    return [{"key": k, "width": v[0], "height": v[1], "label": v[2]}
            for k, v in export_svg.PRESETS.items()]


@router.post("")
def export(req: ExportRequest):
    return export_svg.render(req.spec, req.size)


@router.post("/edit")
def edit(req: EditRequest):
    new_spec = export_edit.edit_spec(req.spec, req.instruction)
    rendered = export_svg.render(new_spec, req.size)
    return {"spec": new_spec, "souls_live": souls.LIVE, **rendered}
