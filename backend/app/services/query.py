"""Safe, semantic-layer-bound query builder over the `appraisals` table.

All column references are validated against the semantic layer; all literals
are bound parameters. Callers never pass raw SQL. A date range is required on
every call (date filtering is global — see DESIGN §3.5).
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import text
from sqlalchemy.orm import Session

from ..semantic.loader import allowed_columns, baseline_filter, dimension, metrics

GRAN_PERIOD = {
    "year": ("appraisal_year::text", "appraisal_year"),
    "quarter": ("year_quarter", "year_quarter"),
    "month": ("to_char(appraisal_date, 'YYYY-MM')", "to_char(appraisal_date, 'YYYY-MM')"),
    "day": ("appraisal_date::text", "appraisal_date"),
}


def resolve_column(name: str) -> str:
    """Map a dimension key OR a raw column name to a validated column."""
    try:
        return dimension(name)["column"]
    except KeyError:
        pass
    if name in allowed_columns():
        return name
    raise ValueError(f"Unknown / disallowed column: {name}")


_TABLES = {"appraisals", "watches"}


def _tbl(name: str | None) -> str:
    """Whitelist the table name — only trusted config sets this, but guard anyway."""
    return name if name in _TABLES else "appraisals"


def metric_expr(metric_key: str) -> tuple[str, str]:
    m = metrics().get(metric_key)
    if not m:
        raise ValueError(f"Unknown metric: {metric_key}")
    agg, col = m["agg"], m["column"]
    if agg == "count":
        return "COUNT(*)", m["label"]
    if col not in allowed_columns():
        raise ValueError(f"Metric column not allowed: {col}")
    return f"{agg.upper()}({col})", m["label"]


_OPS = {"eq": "=", "ne": "!=", "not": "!=", "gt": ">", "gte": ">=", "lt": "<", "lte": "<="}


def _filter_clause(col: str, spec, idx: int, params: dict) -> str:
    """Build one WHERE clause. `spec` is a scalar (=) or a dict {op, value}.

    Supported ops: eq, ne/not, gt, gte, lt, lte, in, not_in, between.
    Columns are validated; all literals are bound parameters.
    """
    if not isinstance(spec, dict):
        params[f"f{idx}"] = spec
        return f"{col} = :f{idx}"
    op = spec.get("op", "eq")
    val = spec.get("value")
    if op in ("in", "not_in"):
        keys = []
        for j, v in enumerate(val or []):
            params[f"f{idx}_{j}"] = v
            keys.append(f":f{idx}_{j}")
        if not keys:
            return "TRUE"
        return f"{col} {'NOT IN' if op == 'not_in' else 'IN'} ({', '.join(keys)})"
    if op == "between":
        params[f"f{idx}_a"], params[f"f{idx}_b"] = val[0], val[1]
        return f"{col} BETWEEN :f{idx}_a AND :f{idx}_b"
    params[f"f{idx}"] = val
    return f"{col} {_OPS.get(op, '=')} :f{idx}"


def _where(date_start: date, date_end: date, filters: dict | None,
           baseline: str | None, params: dict) -> str:
    clauses = ["appraisal_date >= :d_start", "appraisal_date <= :d_end"]
    params["d_start"] = date_start
    params["d_end"] = date_end
    for i, (name, spec) in enumerate((filters or {}).items()):
        clauses.append(_filter_clause(resolve_column(name), spec, i, params))
    bf = baseline_filter(baseline) if baseline else None
    if bf:
        clauses.append(bf)  # baseline filters are from trusted config, not user input
    return " AND ".join(clauses)


# ---- single metric -------------------------------------------------------
def metric_single(db: Session, metric: str, date_start: date, date_end: date,
                  filters: dict | None = None, baseline: str | None = None,
                  table: str = "appraisals") -> dict:
    expr, label = metric_expr(metric)
    params: dict = {}
    where = _where(date_start, date_end, filters, baseline, params)
    sql = f"SELECT {expr} AS value, COUNT(*) AS n FROM {_tbl(table)} WHERE {where}"
    row = db.execute(text(sql), params).one()
    val = float(row.value) if row.value is not None else None
    return {"metric": metric, "label": label, "value": val, "n": int(row.n)}


# ---- metric over time ----------------------------------------------------
def metric_over_time(db: Session, metric: str, date_start: date, date_end: date,
                     granularity: str = "quarter", filters: dict | None = None,
                     split_by: str | None = None, baseline: str | None = None,
                     table: str = "appraisals") -> dict:
    expr, label = metric_expr(metric)
    period_sql, _ = GRAN_PERIOD[granularity]
    tbl = _tbl(table)
    params: dict = {}
    where = _where(date_start, date_end, filters, baseline, params)

    if split_by:
        scol = resolve_column(split_by)
        sql = (f"SELECT {period_sql} AS period, {scol} AS split, {expr} AS value, COUNT(*) AS n "
               f"FROM {tbl} WHERE {where} GROUP BY period, split ORDER BY period")
        rows = db.execute(text(sql), params).all()
        periods = sorted({r.period for r in rows})
        splits = sorted({r.split for r in rows if r.split is not None})
        grid = {(r.period, r.split): r for r in rows}
        series = {s: [(_f(grid.get((p, s)))) for p in periods] for s in splits}
        counts = {s: [int(grid[(p, s)].n) if (p, s) in grid else 0 for p in periods] for s in splits}
        return {"metric": metric, "label": label, "granularity": granularity,
                "periods": periods, "split_by": split_by, "series": series, "counts": counts}

    sql = (f"SELECT {period_sql} AS period, {expr} AS value, COUNT(*) AS n "
           f"FROM {tbl} WHERE {where} GROUP BY period ORDER BY period")
    rows = db.execute(text(sql), params).all()
    periods = [r.period for r in rows]
    return {"metric": metric, "label": label, "granularity": granularity,
            "periods": periods, "series": {label: [_f(r) for r in rows]},
            "counts": {label: [int(r.n) for r in rows]}}


# ---- breakdown -----------------------------------------------------------
def breakdown(db: Session, dimension_name: str, date_start: date, date_end: date,
              metric: str = "piece_count", filters: dict | None = None,
              split_by: str | None = None, table: str = "appraisals") -> dict:
    expr, label = metric_expr(metric)
    dcol = resolve_column(dimension_name)
    tbl = _tbl(table)
    params: dict = {}
    where = _where(date_start, date_end, filters, None, params)

    if split_by:
        scol = resolve_column(split_by)
        sql = (f"SELECT {dcol} AS k, {scol} AS split, {expr} AS value, COUNT(*) AS n "
               f"FROM {tbl} WHERE {where} AND {dcol} IS NOT NULL "
               f"GROUP BY k, split ORDER BY value DESC")
        rows = db.execute(text(sql), params).all()
        splits = sorted({r.split for r in rows if r.split is not None})
        out = {}
        for s in splits:
            srows = [r for r in rows if r.split == s]
            out[s] = [{"key": r.k, "value": _f(r), "n": int(r.n)} for r in srows]
        return {"dimension": dimension_name, "metric": metric, "label": label,
                "split_by": split_by, "groups": out}

    sql = (f"SELECT {dcol} AS k, {expr} AS value, COUNT(*) AS n "
           f"FROM {tbl} WHERE {where} AND {dcol} IS NOT NULL "
           f"GROUP BY k ORDER BY value DESC")
    rows = db.execute(text(sql), params).all()
    return {"dimension": dimension_name, "metric": metric, "label": label,
            "items": [{"key": r.k, "value": _f(r), "n": int(r.n)} for r in rows]}


# ---- share over time -----------------------------------------------------
def share_over_time(db: Session, dimension_name: str, date_start: date, date_end: date,
                    granularity: str = "year", filters: dict | None = None,
                    table: str = "appraisals") -> dict:
    dcol = resolve_column(dimension_name)
    period_sql, _ = GRAN_PERIOD[granularity]
    params: dict = {}
    where = _where(date_start, date_end, filters, None, params)
    sql = (f"SELECT {period_sql} AS period, {dcol} AS k, COUNT(*) AS n "
           f"FROM {_tbl(table)} WHERE {where} AND {dcol} IS NOT NULL "
           f"GROUP BY period, k ORDER BY period")
    rows = db.execute(text(sql), params).all()
    periods = sorted({r.period for r in rows})
    keys = sorted({r.k for r in rows})
    counts = {(r.period, r.k): int(r.n) for r in rows}
    totals = {p: sum(counts.get((p, k), 0) for k in keys) for p in periods}
    shares = {k: [round(counts.get((p, k), 0) / totals[p], 4) if totals[p] else 0.0
                  for p in periods] for k in keys}
    raw_counts = {k: [counts.get((p, k), 0) for p in periods] for k in keys}
    return {"dimension": dimension_name, "granularity": granularity, "periods": periods,
            "keys": keys, "shares": shares, "counts": raw_counts,
            "totals": [totals[p] for p in periods]}


def breakdown_2d(db: Session, dim_a: str, dim_b: str, date_start: date, date_end: date,
                 metric: str = "avg_appraised_value", filters: dict | None = None,
                 table: str = "appraisals") -> dict:
    """Cross-tab: a metric grouped by TWO dimensions (e.g. value by color × clarity).
    Returns grouped-bar shape: x = dim_a values, one series per dim_b value."""
    expr, label = metric_expr(metric)
    cola, colb = resolve_column(dim_a), resolve_column(dim_b)
    params: dict = {}
    where = _where(date_start, date_end, filters, None, params)
    sql = (f"SELECT {cola} AS a, {colb} AS b, {expr} AS value, COUNT(*) AS n "
           f"FROM {_tbl(table)} WHERE {where} AND {cola} IS NOT NULL AND {colb} IS NOT NULL "
           f"GROUP BY a, b")
    rows = db.execute(text(sql), params).all()
    a_keys = sorted({r.a for r in rows})
    b_keys = sorted({r.b for r in rows})
    grid = {(r.a, r.b): r for r in rows}
    series = {b: [(round(float(grid[(a, b)].value), 2) if (a, b) in grid and grid[(a, b)].value is not None else None)
                  for a in a_keys] for b in b_keys}
    return {"dim_a": dim_a, "dim_b": dim_b, "metric": metric, "label": label,
            "a_keys": a_keys, "b_keys": b_keys, "series": series,
            "n": sum(int(r.n) for r in rows)}


def geo_by_state(db: Session, date_start: date, date_end: date, mode: str = "metric",
                 metric: str = "piece_count", dimension: str | None = None,
                 value: str | None = None, filters: dict | None = None,
                 table: str = "appraisals") -> dict:
    """Per-US-state values for a choropleth. mode='share' → fraction where
    dimension == value (e.g. lab-grown share); mode='metric' → any metric."""
    params: dict = {}
    where = _where(date_start, date_end, filters, None, params)
    if mode == "share":
        col = resolve_column(dimension)
        params["gv"] = value
        expr, label = f"AVG(CASE WHEN {col} = :gv THEN 1.0 ELSE 0.0 END)", f"{value} share"
    else:
        expr, label = metric_expr(metric)
    sql = (f"SELECT customer_state AS k, {expr} AS value, COUNT(*) AS n "
           f"FROM {_tbl(table)} WHERE {where} AND customer_state IS NOT NULL GROUP BY k")
    rows = db.execute(text(sql), params).all()
    by_state = {r.k: round(float(r.value), 4) for r in rows if r.value is not None}
    vals = list(by_state.values()) or [0.0]
    return {"by_state": by_state, "min": min(vals), "max": max(vals), "mode": mode,
            "label": label, "n": sum(int(r.n) for r in rows)}


def _f(row) -> float | None:
    if row is None or row.value is None:
        return None
    return round(float(row.value), 2)
