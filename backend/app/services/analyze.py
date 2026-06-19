"""Run the 'souls' over a report fact pack: extract significance-labeled
findings (deterministic) and a plain-language narrative (LLM if configured,
templated otherwise). Never invents numbers."""
from __future__ import annotations

from ..agents import souls
from ..stats import core as st


def analyze_fact_pack(fact_pack: dict) -> dict:
    findings: list[dict] = []

    for sec in fact_pack.get("sections", []):
        kind = sec.get("kind")
        data = sec.get("data", {})
        if kind == "split_share":
            shift = data.get("shift", {})
            for key, sh in shift.items():
                findings.append({
                    "section": sec["title"], "subject": key,
                    "label": sh["label"], "n": sh["n_total"],
                    "detail": f"{key}: share moved {sh['delta_pts']:+.1f} pts "
                              f"({sh['share_first']*100:.1f}% → {sh['share_last']*100:.1f}%).",
                    "caveats": _caveats(sh["n_total"]),
                })
        elif kind == "metric_over_time":
            for split, series in data.get("series", {}).items():
                counts = data.get("counts", {}).get(split, [])
                n = sum(int(c) for c in counts)
                tr = st.series_trend(series, n, counts=[int(c) for c in counts])
                if tr.pct_change is None:
                    continue
                findings.append({
                    "section": sec["title"], "subject": split,
                    "label": tr.label, "n": n,
                    "detail": f"{split}: {data.get('label','value')} {tr.direction} "
                              f"{tr.pct_change:+.0f}% over the period.",
                    "caveats": tr.caveats,
                })

    findings.sort(key=lambda f: ({"Strong": 0, "Directional": 1,
                                  "Part of a broader trend": 2, "Not significant": 3}.get(f["label"], 9),
                                 -(f.get("n") or 0)))
    strong = [f for f in findings if f["label"] in ("Strong", "Directional")]

    summary = (f"{len(strong)} statistically meaningful finding(s) out of {len(findings)} checked. "
               + (f"Headline: {strong[0]['detail']} (confidence {strong[0]['label']}, n={strong[0]['n']:,})."
                  if strong else "Nothing rose above noise in this window — report as stable."))

    narrative = souls.narrate({"summary": summary, "findings": findings[:12],
                               "n_total": fact_pack.get("n_total")}, tier="frontier")

    return {
        "summary": summary,
        "narrative": narrative,
        "souls_live": souls.LIVE,
        "findings": findings,
        "safe_to_say": [f["detail"] for f in strong[:6]],
        "do_not_say": [f["detail"] + "  (within noise / broader trend)"
                       for f in findings if f["label"] in ("Not significant", "Part of a broader trend")][:6],
    }


def _caveats(n: int) -> list[str]:
    if n < st.MIN_N_DIRECTIONAL:
        return [f"Only n={n} — anecdotal."]
    if n < st.MIN_N_STRONG:
        return [f"Modest sample (n={n:,})."]
    return []
