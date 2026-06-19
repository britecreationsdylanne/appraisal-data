"""Trends mode: given an attribute value + timeframe, run the standard battery
and return ranked, significance-labeled findings. Every finding carries n, a
confidence label, caveats, and (where relevant) a baseline comparison so the
writer never over-claims."""
from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from ..semantic.loader import dimension
from ..stats import core as st
from . import query as q

_RANK = {"Strong": 0, "Directional": 1, "Part of a broader trend": 2, "Not significant": 3}


def run_trends(db: Session, dimension_key: str, value: str, date_start: date,
               date_end: date, granularity: str = "year") -> dict:
    dim = dimension(dimension_key)
    if dim.get("placeholder"):
        return {
            "dimension": dimension_key, "dimension_label": dim["label"], "value": value,
            "granularity": granularity, "date_start": str(date_start), "date_end": str(date_end),
            "n_total": 0, "findings": [], "placeholder": True,
            "needs_dataset": dim.get("needs_dataset"),
            "summary": f"The {dim['label']} dataset ({dim.get('needs_dataset')}) isn't connected yet. "
                       f"This is a placeholder — once the watch data is wired in, this trend will run "
                       f"the same battery (share, volume, value over time) as diamonds.",
        }
    baseline_key = dim.get("baseline")
    slice_filters = {dimension_key: value}
    findings: list[dict] = []

    # --- 1. Share of mix over time (within the dimension) ---
    share = q.share_over_time(db, dimension_key, date_start, date_end, granularity)
    if value in share["shares"]:
        s = share["shares"][value]
        counts = share["counts"][value]
        totals = share["totals"]
        n_total = sum(counts)
        tr = st.series_trend([v * 100 for v in s], n_total, counts=totals)
        shift = st.share_shift(counts[0], totals[0], counts[-1], totals[-1]) if len(s) >= 2 else None
        detail = f"Share of {dim['label']} that is '{value}' moved from " \
                 f"{s[0]*100:.1f}% to {s[-1]*100:.1f}% ({tr.direction})."
        findings.append({
            "title": f"{value}: share of mix is {tr.direction}",
            "kind": "share", "label": tr.label, "direction": tr.direction,
            "detail": detail, "caveats": tr.caveats, "n": n_total,
            "p_value": None if shift is None else shift["p_value"],
            "chart": {"type": "line", "x": share["periods"], "y": [round(v * 100, 2) for v in s],
                      "y_label": "% of mix"},
        })

    # --- 2. Volume over time ---
    vol = q.metric_over_time(db, "piece_count", date_start, date_end, granularity, slice_filters)
    vseries = vol["series"].get(vol["label"], [])
    vcounts = vol["counts"].get(vol["label"], [])
    n_vol = sum(int(c) for c in vcounts)
    if vseries:
        tv = st.series_trend(vseries, n_vol, counts=[int(c) for c in vcounts])
        findings.append({
            "title": f"{value}: piece volume is {tv.direction}",
            "kind": "volume", "label": tv.label, "direction": tv.direction,
            "detail": f"Pieces with {dim['label']} = '{value}' went from {int(vseries[0])} to "
                      f"{int(vseries[-1])} per {granularity} "
                      f"({'+' if (tv.pct_change or 0) >= 0 else ''}{tv.pct_change:.0f}%)."
                      if tv.pct_change is not None else "Volume over time.",
            "caveats": tv.caveats, "n": n_vol, "p_value": round(tv.p_value, 5) if tv.p_value == tv.p_value else None,
            "chart": {"type": "bar", "x": vol["periods"], "y": vseries, "y_label": "pieces"},
        })

    # --- 3. Average appraised value vs baseline ---
    sv = q.metric_over_time(db, "avg_appraised_value", date_start, date_end, granularity, slice_filters)
    bv = q.metric_over_time(db, "avg_appraised_value", date_start, date_end, granularity,
                            filters=None, baseline=baseline_key)
    s_series = sv["series"].get(sv["label"], [])
    b_series = bv["series"].get(bv["label"], [])
    n_val = sum(int(c) for c in sv["counts"].get(sv["label"], []))
    if len(s_series) >= 3 and len(b_series) >= 3:
        ts = st.series_trend(s_series, n_val)
        tb = st.series_trend(b_series, n_val)
        cmp = st.compare_to_baseline(ts.slope, tb.slope)
        label = "Part of a broader trend" if cmp["is_broader_trend"] and ts.label in ("Strong", "Directional") else ts.label
        caveats = list(ts.caveats)
        if cmp["note"]:
            caveats.append(cmp["note"])
        findings.append({
            "title": f"{value}: average appraised value is {ts.direction}",
            "kind": "value", "label": label, "direction": ts.direction,
            "detail": f"Average appraised value for '{value}' is {ts.direction} "
                      f"({'+' if (ts.pct_change or 0) >= 0 else ''}{ts.pct_change:.0f}% over the period). "
                      f"Baseline ({dimension(dimension_key).get('baseline')}) is {tb.direction}.",
            "caveats": caveats, "n": n_val,
            "p_value": round(ts.p_value, 5) if ts.p_value == ts.p_value else None,
            "baseline": cmp,
            "chart": {"type": "line", "x": sv["periods"],
                      "series": {value: s_series, "baseline": b_series}, "y_label": "avg appraised $"},
        })

    findings.sort(key=lambda f: (_RANK.get(f["label"], 9), -(f.get("n") or 0)))
    return {
        "dimension": dimension_key, "dimension_label": dim["label"], "value": value,
        "granularity": granularity, "date_start": str(date_start), "date_end": str(date_end),
        "n_total": n_vol, "findings": findings,
        "summary": _headline(findings, value, dim["label"]),
    }


def _headline(findings: list[dict], value: str, dim_label: str) -> str:
    strong = [f for f in findings if f["label"] in ("Strong", "Directional")]
    if not strong:
        return (f"No statistically meaningful trend for {dim_label} '{value}' in this window. "
                f"Numbers moved within noise — safe to say it's stable, not to claim a trend.")
    lead = strong[0]
    return f"Most notable: {lead['detail']} (confidence: {lead['label']}, n={lead['n']:,})."
