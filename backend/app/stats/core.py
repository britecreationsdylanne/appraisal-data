"""Deterministic statistics. Every claim the tool makes about a trend or a
difference is decided here, with sample size and significance attached.

The honesty rules (min-n gating, baseline comparison) come from
semantic/rules.yaml so they're configurable in one place.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
from scipy import stats

from ..semantic.loader import rules

_R = rules()["significance"]
_L = rules()["labels"]

MIN_N_STRONG = _R["min_n_strong"]
MIN_N_DIRECTIONAL = _R["min_n_directional"]
ALPHA = _R["alpha"]
BASELINE_TOL = _R["baseline_match_tolerance"]


@dataclass
class TrendResult:
    slope: float
    p_value: float
    r: float
    direction: str          # "up" | "down" | "flat"
    pct_change: float | None  # first -> last period, if meaningful
    n: int
    label: str
    caveats: list[str] = field(default_factory=list)


def _label(n: int, p_value: float) -> str:
    if n < MIN_N_DIRECTIONAL or math.isnan(p_value):
        return _L["not_significant"]
    if p_value >= ALPHA:
        return _L["not_significant"]
    if n < MIN_N_STRONG:
        return _L["directional"]
    return _L["strong"]


def series_trend(y: list[float], n_total: int, counts: list[int] | None = None) -> TrendResult:
    """Linear trend of a numeric series over evenly-spaced periods."""
    y = [v for v in y if v is not None and not (isinstance(v, float) and math.isnan(v))]
    caveats: list[str] = []
    if len(y) < 3:
        return TrendResult(0, float("nan"), 0, "flat", None, n_total, _L["not_significant"],
                           ["Too few periods to assess a trend (need 3+)."])
    x = np.arange(len(y), dtype=float)
    reg = stats.linregress(x, y)
    slope, p_value, r = float(reg.slope), float(reg.pvalue), float(reg.rvalue)
    direction = "up" if slope > 0 else "down" if slope < 0 else "flat"
    first, last = float(y[0]), float(y[-1])
    pct = ((last - first) / first * 100.0) if first not in (0, None) else None

    label = _label(n_total, p_value)
    if n_total < MIN_N_STRONG:
        caveats.append(f"Sample is modest (n={n_total:,}); treat as directional, not definitive.")
    if counts and min(counts) < MIN_N_DIRECTIONAL:
        caveats.append(f"Some periods are thin (smallest n={min(counts)}); per-period values are noisy.")
    if label == _L["not_significant"]:
        caveats.append("Change is within noise — do not report this as a real trend.")
    return TrendResult(slope, p_value, r, direction, pct, n_total, label, caveats)


def two_proportion_test(c1: int, n1: int, c2: int, n2: int) -> tuple[float, float]:
    """Two-proportion z-test. Returns (z, p_value). Used for share shifts."""
    if n1 == 0 or n2 == 0:
        return float("nan"), float("nan")
    p1, p2 = c1 / n1, c2 / n2
    p_pool = (c1 + c2) / (n1 + n2)
    se = math.sqrt(p_pool * (1 - p_pool) * (1 / n1 + 1 / n2))
    if se == 0:
        return float("nan"), float("nan")
    z = (p2 - p1) / se
    p = 2 * (1 - stats.norm.cdf(abs(z)))
    return float(z), float(p)


def share_shift(c_first: int, n_first: int, c_last: int, n_last: int) -> dict:
    """Significance of a share moving between the first and last period."""
    z, p = two_proportion_test(c_first, n_first, c_last, n_last)
    s_first = c_first / n_first if n_first else 0.0
    s_last = c_last / n_last if n_last else 0.0
    n_total = n_first + n_last
    return {
        "share_first": round(s_first, 4),
        "share_last": round(s_last, 4),
        "delta_pts": round((s_last - s_first) * 100, 2),
        "z": None if math.isnan(z) else round(z, 3),
        "p_value": None if math.isnan(p) else round(p, 5),
        "n_total": n_total,
        "label": _label(n_total, p),
    }


def compare_to_baseline(slice_slope: float, baseline_slope: float) -> dict:
    """Decide whether a slice's movement is really just the parent trend.

    If the slice and its baseline move the same direction at a similar rate,
    the finding is reframed as 'part of a broader trend' rather than slice-specific.
    """
    slice_slope, baseline_slope = float(slice_slope), float(baseline_slope)
    same_dir = bool((slice_slope > 0) == (baseline_slope > 0))
    if baseline_slope == 0:
        broader = bool(same_dir and abs(slice_slope) < 1e-9)
    else:
        ratio = abs(slice_slope) / abs(baseline_slope)
        broader = bool(same_dir and (1 - BASELINE_TOL) <= ratio <= (1 + BASELINE_TOL))
    return {
        "slice_slope": round(slice_slope, 4),
        "baseline_slope": round(baseline_slope, 4),
        "same_direction": same_dir,
        "is_broader_trend": broader,
        "note": ("This movement tracks the overall baseline — likely part of a broader trend, "
                 "not specific to this attribute.") if broader else
                ("This attribute moves differently from the overall baseline — the effect looks "
                 "specific to it." if same_dir is False or not broader else ""),
    }
