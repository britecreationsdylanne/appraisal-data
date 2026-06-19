"""Fact Finder: read a blog draft, summarize it, and suggest real, runnable
data questions the writer can pull — plus flag claims the data can't support.
LLM-powered when souls are live; deterministic keyword fallback otherwise."""
from __future__ import annotations

import re

from ..agents import souls
from ..semantic.loader import attribute_menu, metrics

_STOP = {"other", "all", "a", "b", "i", "light", "none"}


def _catalog() -> dict:
    return {
        "metrics": list(metrics().keys()),
        "dimensions": {d["key"]: d["values"] for d in attribute_menu() if not d["placeholder"]},
    }


def analyze(text: str) -> dict:
    llm = souls.fact_finder(text, _catalog())
    if llm and isinstance(llm, dict) and llm.get("suggestions"):
        llm.setdefault("claim_checks", [])
        llm.setdefault("topics", [])
        llm["souls_live"] = True
        return llm
    return _deterministic(text)


def _deterministic(text: str) -> dict:
    lo = f" {text.lower()} "
    matched: list[tuple[str, str]] = []
    for d in attribute_menu():
        if d.get("placeholder"):
            continue
        for v in d["values"]:
            vl = str(v).lower()
            if vl in _STOP or len(vl) < 3:
                continue
            if re.search(rf"\b{re.escape(vl)}\b", lo):
                matched.append((d["label"], v))  # capture every value mentioned, not just one

    suggestions: list[dict] = []
    if any(w in lo for w in ["lab", "natural", "diamond", "engagement"]):
        suggestions.append({
            "question": "Average appraised value, natural vs lab, by year",
            "rationale": "Anchors the lab-vs-natural angle with the value trend.",
        })
    for _, v in matched[:5]:
        suggestions.append({
            "question": f"Average appraised value of {v} over time",
            "rationale": f"Your draft mentions {v} — show how its appraised value has trended.",
        })
    if not suggestions:
        suggestions = [
            {"question": "How many pieces by year", "rationale": "A volume baseline to ground the piece."},
            {"question": "Average appraised value over time", "rationale": "The headline trend across all appraisals."},
        ]

    words = len(text.split())
    vals = [v for _, v in matched][:6]
    if vals:
        summary = (f"Your draft runs ~{words} words and references {', '.join(vals)}. "
                   f"Here are stats you could pull to back it up — review and run any of them.")
    else:
        summary = (f"Your draft runs ~{words} words. I didn't spot specific attributes, so here are "
                   f"solid general stats to ground it.")

    return {
        "summary": summary,
        "topics": vals,
        "suggestions": suggestions[:6],
        "claim_checks": [],
        "souls_live": False,
    }
