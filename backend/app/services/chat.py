"""Chat mode: a natural-language question becomes a structured, semantic-layer
query, executed deterministically, and answered WITH sample size + caveat every
time. The LLM (if configured) plans and phrases; the numbers are always real."""
from __future__ import annotations

import re
from datetime import date

from sqlalchemy.orm import Session

from ..agents import souls
from ..models import ChatLog
from ..semantic.loader import attribute_menu, dimension, metrics
from ..stats import core as st
from . import query as q

# values too ambiguous to keyword-match on
_STOP_VALUES = {"other", "all", "a", "b", "i", "light"}


def _keyword_plan(question: str) -> dict:
    lo = f" {question.lower()} "
    if any(w in lo for w in ["how many", "count", "number of", " volume", "pieces"]):
        metric = "piece_count"
    elif "total value" in lo or "total appraised" in lo:
        metric = "total_appraised_value"
    elif "carat" in lo:
        metric = "avg_carat"
    elif "sales price" in lo or "sale price" in lo or "sold for" in lo:
        metric = "avg_sales_price"
    elif any(w in lo for w in ["value", "appraised", "worth", "price"]):
        metric = "avg_appraised_value"
    else:
        metric = "piece_count"

    filters: dict = {}
    # special synonyms
    if "lab-grown" in lo or "lab grown" in lo or " lab " in lo:
        filters["source"] = "lab"
    elif "natural" in lo:
        filters["source"] = "natural"
    if "engagement" in lo:
        filters["briteco_category"] = "Engagement Ring"

    for d in attribute_menu():
        if d["key"] in filters:
            continue
        for v in d["values"]:
            vl = str(v).lower()
            if vl in _STOP_VALUES or len(vl) < 3:
                continue
            if re.search(rf"\b{re.escape(vl)}\b", lo):
                filters[d["key"]] = v
                break

    over_time = any(w in lo for w in ["over time", "trend", "by year", "by quarter",
                                      "each year", "per year", "yearly", "quarterly", "by month"])
    gran = "quarter" if "quarter" in lo else "month" if "month" in lo else "year"
    split_by = None
    if "vs lab" in lo or "lab vs" in lo or "by source" in lo or "vs natural" in lo:
        split_by = "source"
        filters.pop("source", None)
    return {"metric": metric, "filters": filters, "over_time": over_time,
            "granularity": gran, "split_by": split_by}


def _describe_filters(filters: dict) -> str:
    if not filters:
        return "all pieces"
    parts = []
    for k, v in filters.items():
        try:
            parts.append(f"{dimension(k)['label']} = {v}")
        except KeyError:
            parts.append(f"{k} = {v}")
    return ", ".join(parts)


def _fmt(metric: str, value) -> str:
    if value is None:
        return "n/a"
    fmt = metrics()[metric].get("format")
    if fmt == "currency":
        return f"${value:,.0f}"
    if fmt == "decimal2":
        return f"{value:.2f}"
    return f"{int(value):,}"


def ask(db: Session, question: str, date_start: date, date_end: date, user: str = "local") -> dict:
    plan = souls.plan_query_llm(question, metrics(), attribute_menu()) or _keyword_plan(question)
    plan.setdefault("filters", {})
    plan.setdefault("granularity", "year")
    metric = plan.get("metric", "piece_count")
    filters = plan.get("filters") or {}

    if plan.get("over_time"):
        res = q.metric_over_time(db, metric, date_start, date_end, plan["granularity"],
                                 filters=filters, split_by=plan.get("split_by"))
        n = sum(sum(int(c) for c in cs) for cs in res["counts"].values())
        answer = (f"{metrics()[metric]['label']} for {_describe_filters(filters)}, "
                  f"by {plan['granularity']} ({date_start.year}–{date_end.year}). "
                  f"Based on {n:,} pieces.")
        data = {"kind": "over_time", "result": res}
    else:
        r = q.metric_single(db, metric, date_start, date_end, filters)
        n = r["n"]
        answer = (f"{r['label']} for {_describe_filters(filters)} "
                  f"({date_start} to {date_end}) is {_fmt(metric, r['value'])}, based on {n:,} pieces.")
        data = {"kind": "single", "result": r}

    caveat = _caveat(n)
    confidence = "Strong" if n >= st.MIN_N_STRONG else "Directional" if n >= st.MIN_N_DIRECTIONAL else "Not significant"

    narrative = souls.narrate({"question": question, "plan": plan, "data": data,
                               "n": n, "confidence": confidence})

    result = {
        "question": question, "plan": plan, "answer": narrative or answer,
        "deterministic_answer": answer, "data": data, "n": n,
        "confidence": confidence, "caveat": caveat,
        "souls_live": souls.LIVE,
        "fact": {"label": _describe_filters(filters), "metric": metrics()[metric]["label"],
                 "n": n, "period": f"{date_start} to {date_end}", "confidence": confidence},
    }

    log = ChatLog(owner=user, shared=False, question=question, answer=result["answer"],
                  metric=metric, n=n, confidence=confidence, caveat=caveat, plan=plan,
                  date_start=date_start, date_end=date_end)
    db.add(log)
    db.commit()
    db.refresh(log)
    result["id"] = log.id
    return result


def _caveat(n: int) -> str:
    if n < st.MIN_N_DIRECTIONAL:
        return f"Only {n} matching pieces — too few to be reliable. Treat as anecdotal, not a stat."
    if n < st.MIN_N_STRONG:
        return f"Modest sample (n={n:,}). Directional — fine for color, not for a headline claim."
    return f"Solid sample (n={n:,})."
