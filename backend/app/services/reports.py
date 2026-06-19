"""Report runner: execute a saved-template spec over a date range into a
fact pack (every data point, with n + caveats). Pure data — the 'souls' add
interpretation separately via the Analyze step."""
from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from ..stats import core as st
from . import query as q

LOW_N = st.MIN_N_DIRECTIONAL


def run_report(db: Session, spec: dict, date_start: date, date_end: date,
               granularity: str = "quarter") -> dict:
    default_table = spec.get("table", "appraisals")
    sections_out = []
    for sec in spec.get("sections", []):
        kind = sec.get("kind")
        filters = sec.get("filters")
        tbl = sec.get("table", default_table)
        try:
            if kind == "note":
                sections_out.append({"title": sec["title"], "kind": "note", "note": sec.get("note", "")})
                continue
            if kind == "callout":
                r = q.metric_single(db, sec["metric"], date_start, date_end, filters, table=tbl)
                sections_out.append({"title": sec["title"], "kind": kind, "data": r,
                                     "n": r["n"], "caveats": _n_caveat(r["n"])})
            elif kind == "metric_over_time":
                r = q.metric_over_time(db, sec["metric"], date_start, date_end, granularity,
                                       filters=filters, split_by=sec.get("split_by"), table=tbl)
                n = sum(sum(int(c) for c in cs) for cs in r["counts"].values())
                sections_out.append({"title": sec["title"], "kind": kind, "data": r,
                                     "n": n, "caveats": _n_caveat(n)})
            elif kind == "breakdown":
                r = q.breakdown(db, sec["dimension"], date_start, date_end,
                                metric=sec.get("metric", "piece_count"),
                                filters=filters, split_by=sec.get("split_by"), table=tbl)
                sections_out.append({"title": sec["title"], "kind": kind, "data": r})
            elif kind == "split_share":
                r = q.share_over_time(db, sec["dimension"], date_start, date_end, granularity, filters, table=tbl)
                r["shift"] = _share_shifts(r)
                sections_out.append({"title": sec["title"], "kind": kind, "data": r})
            elif kind == "breakdown_2d":
                r = q.breakdown_2d(db, sec["dim_a"], sec["dim_b"], date_start, date_end,
                                   metric=sec.get("metric", "avg_appraised_value"), filters=filters, table=tbl)
                sections_out.append({"title": sec["title"], "kind": kind, "data": r,
                                     "n": r["n"], "caveats": _n_caveat(r["n"])})
            elif kind == "geo":
                r = q.geo_by_state(db, date_start, date_end, mode=sec.get("mode", "metric"),
                                   metric=sec.get("metric", "piece_count"),
                                   dimension=sec.get("dimension"), value=sec.get("value"),
                                   filters=filters, table=tbl)
                sections_out.append({"title": sec["title"], "kind": kind, "data": r,
                                     "n": r["n"], "caveats": _n_caveat(r["n"])})
            else:
                sections_out.append({"title": sec.get("title", "?"), "kind": "note",
                                     "note": f"Unsupported section kind: {kind}"})
        except Exception as e:  # keep the report resilient — one bad section shouldn't kill it
            sections_out.append({"title": sec.get("title", "?"), "kind": "error", "error": str(e)})

    total = q.metric_single(db, "piece_count", date_start, date_end, table=default_table)
    return {
        "date_start": str(date_start), "date_end": str(date_end), "granularity": granularity,
        "n_total": total["n"], "sections": sections_out,
    }


def _n_caveat(n: int) -> list[str]:
    if n < LOW_N:
        return [f"Only {n} pieces match — too few to be reliable; treat as anecdotal."]
    if n < st.MIN_N_STRONG:
        return [f"Modest sample (n={n:,}); directional, not definitive."]
    return []


def _share_shifts(share: dict) -> dict:
    out = {}
    periods = share["periods"]
    if len(periods) < 2:
        return out
    totals = share["totals"]
    for k, counts in share["counts"].items():
        out[k] = st.share_shift(counts[0], totals[0], counts[-1], totals[-1])
    return out
