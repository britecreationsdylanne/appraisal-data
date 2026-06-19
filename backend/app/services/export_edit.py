"""Chat-to-edit for exported images. Tries the LLM editor (when souls are live);
otherwise a deterministic parser handles the common asks: background color,
accent color, and chart type."""
from __future__ import annotations

import copy

from ..agents import souls
from .export_svg import COLOR_NAMES


def _find_color(lo: str) -> str | None:
    for name in COLOR_NAMES:
        if name in lo:
            return name
    # raw hex
    import re
    m = re.search(r"#[0-9a-f]{6}|#[0-9a-f]{3}", lo)
    return m.group(0) if m else None


def _deterministic_edit(spec: dict, instruction: str) -> dict:
    s = copy.deepcopy(spec)
    lo = f" {instruction.lower()} "
    color = _find_color(lo)

    if "bar" in lo and "chart" in lo or "as bars" in lo or "make it bars" in lo or "bar graph" in lo:
        if s.get("kind") != "stats":
            s["kind"] = "bar"
    if "line" in lo and ("chart" in lo or "graph" in lo) or "as a line" in lo:
        if s.get("kind") != "stats":
            s["kind"] = "line"

    if color:
        if "background" in lo or " bg " in lo or "behind" in lo:
            s["background"] = color
        elif any(w in lo for w in ["accent", "bars", "bar color", "line color", "lines", "series", "highlight"]):
            s["accent"] = color
        else:
            # a lone color request most commonly means the background
            s["background"] = color

    # title: "title to X" / "change the title to X"
    if "title to " in lo:
        idx = instruction.lower().find("title to ")
        new_title = instruction[idx + len("title to "):].strip(" .\"'")
        if new_title:
            s["title"] = new_title

    return s


def edit_spec(spec: dict, instruction: str) -> dict:
    llm = souls.edit_export(spec, instruction)
    if llm and isinstance(llm, dict):
        return llm
    return _deterministic_edit(spec, instruction)
