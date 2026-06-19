"""The 'souls' — the AI layer that interprets numbers for a non-data writer.

Design contract:
  * The math is ALWAYS done by the stats core / query layer (deterministic).
  * Souls only PLAN queries and INTERPRET results. They never invent numbers.
  * Without an ANTHROPIC_API_KEY the souls fall back to deterministic templates,
    so the tool is fully usable offline — just less fluent.

Model tiers follow the model-migration skill (frontier / standard / economy)
and are read from config so /update-models can migrate them.
"""
from __future__ import annotations

import json

from ..config import get_settings

settings = get_settings()
LIVE = settings.souls_live

_client = None
if LIVE:
    try:
        import anthropic
        _client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    except Exception:
        _client = None
        LIVE = False


def _complete(system: str, user: str, tier: str = "standard", max_tokens: int = 900) -> str | None:
    if not _client:
        return None
    model = {"frontier": settings.model_frontier,
             "standard": settings.model_standard,
             "economy": settings.model_economy}.get(tier, settings.model_standard)
    try:
        msg = _client.messages.create(
            model=model, max_tokens=max_tokens, system=system,
            messages=[{"role": "user", "content": user}],
        )
        return "".join(b.text for b in msg.content if getattr(b, "type", "") == "text")
    except Exception:
        return None


# --- Planner: NL question -> structured query (LLM, JSON-constrained) ------
PLANNER_SYSTEM = (
    "You translate a jewelry-appraisal data question into a STRICT JSON query plan. "
    "You may ONLY use the provided metrics, dimensions, and dimension values. "
    "Never invent columns or values. Respond with JSON only, no prose.\n"
    "Schema: {\"metric\": <metric_key>, \"filters\": {<dimension_key>: <value>}, "
    "\"over_time\": <bool>, \"granularity\": \"year\"|\"quarter\"|\"month\", "
    "\"split_by\": <dimension_key or null>}"
)


def plan_query_llm(question: str, metrics: dict, menu: list[dict]) -> dict | None:
    if not _client:
        return None
    catalog = {
        "metrics": list(metrics.keys()),
        "dimensions": {d["key"]: d["values"] for d in menu},
    }
    user = f"CATALOG:\n{json.dumps(catalog)}\n\nQUESTION: {question}\n\nReturn the JSON plan."
    raw = _complete(PLANNER_SYSTEM, user, tier="standard", max_tokens=400)
    if not raw:
        return None
    try:
        start, end = raw.find("{"), raw.rfind("}")
        return json.loads(raw[start:end + 1])
    except Exception:
        return None


# --- Narrator/Analyst/Skeptic over a fact pack or chat result -------------
ANALYST_SYSTEM = (
    "You are a careful data analyst writing for a NON-technical writer at a jewelry "
    "insurer. You are given ALREADY-COMPUTED numbers with sample sizes (n), significance "
    "labels, and baseline comparisons. Rules you MUST follow:\n"
    "1. Never state a number that isn't in the input. Never recompute.\n"
    "2. Always pair a claim with its sample size and confidence label.\n"
    "3. If a finding is labeled 'Not significant' or 'Part of a broader trend', say so plainly "
    "and do NOT frame it as a discovery specific to the attribute.\n"
    "4. Distinguish a narrow finding from a broad category trend.\n"
    "5. Be concise, plain-language, and honest. No hype. No causal claims unless supported.\n"
    "Return: a 2-4 sentence summary, then up to 4 bullet 'safe-to-say' facts."
)


def narrate(context: dict, tier: str = "frontier") -> str | None:
    if not _client:
        return None
    return _complete(ANALYST_SYSTEM, json.dumps(context, default=str), tier=tier, max_tokens=900)


# --- Image editor: tweak an export spec from a natural-language instruction --
EDIT_SYSTEM = (
    "You edit a JSON spec for a branded infographic. Given the current spec and an instruction, "
    "return the FULL modified spec as JSON only (no prose). Allowed fields: title, subtitle, footer, "
    "kind ('line'|'bar'|'stats'), labels, series, stats, background (color name or #hex), "
    "accent (color name or #hex). NEVER invent or change data values (labels/series/stats) unless the "
    "instruction explicitly asks. Only change what the instruction asks for."
)


def edit_export(spec: dict, instruction: str) -> dict | None:
    if not _client:
        return None
    raw = _complete(EDIT_SYSTEM, json.dumps({"spec": spec, "instruction": instruction}),
                    tier="standard", max_tokens=1500)
    if not raw:
        return None
    try:
        start, end = raw.find("{"), raw.rfind("}")
        return json.loads(raw[start:end + 1])
    except Exception:
        return None


# --- Fact Finder: read a blog draft, suggest data to pull, flag claims --------
FACTFINDER_SYSTEM = (
    "You help a NON-technical writer support a jewelry blog draft with real data from a "
    "jewelry-appraisal database. You are given the draft and a CATALOG of the only metrics, "
    "dimensions, and dimension values available. Respond with JSON only:\n"
    '{"summary": <2-3 sentence plain summary of the draft>, '
    '"suggestions": [{"question": <a natural-language question answerable ONLY with catalog '
    'vocabulary>, "rationale": <why this stat helps the piece>}], '
    '"claim_checks": [{"claim": <a factual claim made in the draft>, "checkable": <bool — can '
    'this dataset verify it?>, "note": <how to check it, or why not>}]}\n'
    "Rules: 3-6 suggestions; never invent metrics/values; prefer questions that surface a real "
    "trend; flag claims the data CANNOT support so the writer does not over-claim."
)


def fact_finder(text: str, catalog: dict) -> dict | None:
    if not _client:
        return None
    user = f"CATALOG:\n{json.dumps(catalog)}\n\nDRAFT:\n{text[:8000]}\n\nReturn the JSON."
    raw = _complete(FACTFINDER_SYSTEM, user, tier="frontier", max_tokens=1800)
    if not raw:
        return None
    try:
        start, end = raw.find("{"), raw.rfind("}")
        return json.loads(raw[start:end + 1])
    except Exception:
        return None
