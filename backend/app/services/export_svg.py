"""Branded static infographic export. Renders a self-contained SVG (BriteCo
colors + Gilroy) at preset sizes from a chart spec. Lightweight — no headless
browser needed. Every export carries the period + sample size in the footer so
a stat is never orphaned from its caveat.

Supports kind = "line" | "bar" | "stats", plus optional `background` and
`accent` overrides (used by chat-to-edit)."""
from __future__ import annotations

import math
from html import escape

# BriteCo palette (briteco-branding skill)
NAVY = "#272D3F"
TEAL = "#008182"
MINT = "#31D7CA"
ORANGE = "#FC883A"
SLATE = "#7DA3AF"
FROST = "#F4F7FC"
CLOUD = "#E1E7EF"
SERIES = ["#008182", "#FC883A", "#9b87f5", "#4285F4", "#31D7CA", "#7DA3AF"]

# Named colors people might say in a chat tweak.
COLOR_NAMES = {
    "teal": TEAL, "navy": NAVY, "mint": MINT, "orange": ORANGE, "slate": SLATE,
    "frost": FROST, "cloud": CLOUD, "white": "#FFFFFF", "purple": "#9b87f5",
    "blue": "#4285F4", "coral": "#D73D4F", "gray": "#7DA3AF", "grey": "#7DA3AF",
    "black": "#272D3F", "green": "#1E9E6A", "pink": "#E86A9A", "cream": "#FBF7EF",
}

PRESETS = {
    "ig_square": (1080, 1080, "Instagram Square 1:1"),
    "ig_portrait": (1080, 1350, "Instagram Portrait 4:5"),
    "story": (1080, 1920, "Story / Reel 9:16"),
    "blog": (1200, 675, "Blog 16:9"),
    "pinterest": (1000, 1500, "Pinterest 2:3"),
}
FONT = "'Gilroy', system-ui, -apple-system, 'Segoe UI', sans-serif"


def resolve_color(value, default):
    if not value:
        return default
    v = str(value).strip().lower()
    if v in COLOR_NAMES:
        return COLOR_NAMES[v]
    if v.startswith("#") and len(v) in (4, 7):
        return v
    return default


def _is_dark(hex_color: str) -> bool:
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    try:
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    except ValueError:
        return False
    return (0.299 * r + 0.587 * g + 0.114 * b) < 140


def render(spec: dict, size: str = "ig_square") -> dict:
    w, h, size_label = PRESETS.get(size, PRESETS["ig_square"])
    title = escape(spec.get("title", "Appraisal Data"))
    subtitle = escape(spec.get("subtitle", ""))
    footer = escape(spec.get("footer", ""))
    kind = spec.get("kind", "bar")

    bg = resolve_color(spec.get("background"), FROST)
    ink = NAVY if not _is_dark(bg) else "#FFFFFF"
    sub_ink = SLATE if not _is_dark(bg) else "#C9D6DE"
    accent = resolve_color(spec.get("accent"), None)
    palette = ([accent] + [c for c in SERIES if c != accent]) if accent else SERIES

    pad = int(w * 0.07)

    header = f"""
  <rect width="{w}" height="{h}" fill="{bg}"/>
  <rect x="0" y="0" width="{w}" height="{int(h*0.16)}" fill="{TEAL}"/>
  <circle cx="{pad+14}" cy="{int(h*0.08)}" r="14" fill="{MINT}"/>
  <path d="M {pad+8} {int(h*0.08)} l 4 5 l 8 -10" stroke="{NAVY}" stroke-width="3" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
  <text x="{pad+38}" y="{int(h*0.066)}" fill="#FFFFFF" font-size="{int(h*0.018)+10}" font-weight="600">BriteCo · Appraisal Data Research</text>"""

    if kind == "stats":
        body = _stats(spec.get("stats", []), w, h, pad, ink, sub_ink, palette)
        title_block = (
            f'<text x="{pad}" y="{int(h*0.27)}" fill="{ink}" font-size="{int(w*0.045)}" font-weight="600">{title}</text>'
            f'<text x="{pad}" y="{int(h*0.27)+34}" fill="{sub_ink}" font-size="{int(w*0.02)}">{subtitle}</text>'
        )
    elif kind == "pie":
        labels = [escape(str(x)) for x in spec.get("labels", [])]
        series = spec.get("series", {})
        values = list(series.values())[0] if series else []
        body = _pie(labels, values, w, h, pad, ink, palette)
        title_block = (
            f'<text x="{pad}" y="{int(h*0.27)}" fill="{ink}" font-size="{int(w*0.04)}" font-weight="600">{title}</text>'
            f'<text x="{pad}" y="{int(h*0.27)+32}" fill="{sub_ink}" font-size="{int(w*0.02)}">{subtitle}</text>'
        )
    else:
        plot_top = int(h * 0.30)
        plot_bottom = h - int(h * 0.14)
        plot_left = pad + 10
        plot_right = w - pad
        labels = [escape(str(x)) for x in spec.get("labels", [])]
        series = spec.get("series", {})
        all_vals = [v for vs in series.values() for v in vs if v is not None] or [0, 1]
        vmax = max(all_vals) * 1.15 or 1
        if kind == "line":
            parts = _line(labels, series, plot_left, plot_top, plot_right - plot_left, plot_bottom - plot_top, vmax, plot_bottom, palette, sub_ink)
        else:
            parts = _bars(labels, series, plot_left, plot_top, plot_right - plot_left, plot_bottom - plot_top, vmax, plot_bottom, palette, sub_ink)
        body = _legend(series, plot_left, plot_top - 28, palette, ink) + "".join(parts)
        title_block = (
            f'<text x="{pad}" y="{plot_top-58}" fill="{ink}" font-size="{int(w*0.04)}" font-weight="600">{title}</text>'
            f'<text x="{pad}" y="{plot_top-30}" fill="{sub_ink}" font-size="{int(w*0.02)}">{subtitle}</text>'
        )

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" font-family="{FONT}">{header}
  {title_block}
  {body}
  <text x="{pad}" y="{h-int(h*0.05)}" fill="{sub_ink}" font-size="{int(w*0.016)}">{footer}</text>
  <text x="{w-pad}" y="{h-int(h*0.05)}" text-anchor="end" fill="{CLOUD}" font-size="{int(w*0.014)}">{size_label}</text>
</svg>"""
    return {"svg": svg, "width": w, "height": h, "size": size, "size_label": size_label}


def _stats(stats, w, h, pad, ink, sub_ink, palette):
    out = []
    y = int(h * 0.36)
    row_h = int((h * 0.5) / max(len(stats), 1))
    row_h = min(row_h, int(h * 0.14))
    for i, s in enumerate(stats[:6]):
        c = palette[i % len(palette)]
        out.append(f'<rect x="{pad}" y="{y-8}" width="6" height="{row_h-20}" rx="3" fill="{c}"/>')
        out.append(f'<text x="{pad+22}" y="{y+int(row_h*0.28)}" fill="{ink}" font-size="{int(w*0.05)}" font-weight="600">{escape(str(s.get("value","")))}</text>')
        out.append(f'<text x="{pad+22}" y="{y+int(row_h*0.5)}" fill="{ink}" font-size="{int(w*0.022)}">{escape(str(s.get("label","")))}</text>')
        if s.get("sub"):
            out.append(f'<text x="{pad+22}" y="{y+int(row_h*0.68)}" fill="{sub_ink}" font-size="{int(w*0.016)}">{escape(str(s.get("sub")))}</text>')
        y += row_h
    return "".join(out)


def _pt(cx, cy, rad, deg):
    a = math.radians(deg)
    return f"{cx + rad * math.cos(a):.1f} {cy + rad * math.sin(a):.1f}"


def _pie(labels, values, w, h, pad, ink, palette):
    pairs = [(labels[i] if i < len(labels) else "?", float(values[i] or 0)) for i in range(len(values))]
    pairs.sort(key=lambda p: p[1], reverse=True)
    if len(pairs) > 9:
        head = pairs[:9]
        others = sum(v for _, v in pairs[9:])
        pairs = head + [("Others", others)]
    total = sum(v for _, v in pairs) or 1

    R = int(min(w, h) * 0.26)
    r = int(R * 0.55)
    cx = pad + R + 10
    cy = int(h * 0.60)
    out, angle = [], -90.0
    for i, (lab, v) in enumerate(pairs):
        frac = v / total
        a1 = angle + frac * 360
        large = 1 if frac > 0.5 else 0
        c = palette[i % len(palette)]
        out.append(
            f'<path d="M {_pt(cx,cy,R,angle)} A {R} {R} 0 {large} 1 {_pt(cx,cy,R,a1)} '
            f'L {_pt(cx,cy,r,a1)} A {r} {r} 0 {large} 0 {_pt(cx,cy,r,angle)} Z" fill="{c}"/>'
        )
        if frac > 0.03:
            mid = (angle + a1) / 2
            lx, ly = _pt(cx, cy, R * 0.78, mid).split()
            out.append(f'<text x="{lx}" y="{ly}" text-anchor="middle" fill="#FFFFFF" font-size="16" font-weight="600">{frac*100:.0f}%</text>')
        angle = a1
    # legend
    lx = cx + R + 30
    ly = cy - len(pairs) * 13
    for i, (lab, v) in enumerate(pairs):
        c = palette[i % len(palette)]
        out.append(f'<rect x="{lx}" y="{ly-13}" width="16" height="16" rx="3" fill="{c}"/>')
        out.append(f'<text x="{lx+24}" y="{ly}" fill="{ink}" font-size="18">{escape(str(lab))} · {v/total*100:.0f}%</text>')
        ly += 30
    return "".join(out)


def _legend(series, x, y, palette, ink):
    out, cx = [], x
    for i, name in enumerate(series.keys()):
        c = palette[i % len(palette)]
        out.append(f'<rect x="{cx}" y="{y-12}" width="14" height="14" rx="3" fill="{c}"/>')
        out.append(f'<text x="{cx+20}" y="{y}" fill="{ink}" font-size="18">{escape(str(name))}</text>')
        cx += 40 + len(str(name)) * 11
    return "".join(out)


def _bars(labels, series, x0, y0, w, h, vmax, ybase, palette, sub_ink):
    out = []
    names = list(series.keys())
    n_groups = len(labels)
    if n_groups == 0:
        return out
    group_w = w / n_groups
    bar_w = group_w * 0.7 / max(len(names), 1)
    for gi, lab in enumerate(labels):
        gx = x0 + gi * group_w + group_w * 0.15
        for si, name in enumerate(names):
            vals = series[name]
            v = vals[gi] if gi < len(vals) and vals[gi] is not None else 0
            bh = (v / vmax) * h
            bx = gx + si * bar_w
            out.append(f'<rect x="{bx:.1f}" y="{ybase-bh:.1f}" width="{bar_w*0.9:.1f}" height="{bh:.1f}" rx="3" fill="{palette[si % len(palette)]}"/>')
        out.append(f'<text x="{gx+(len(names)*bar_w)/2:.1f}" y="{ybase+26}" text-anchor="middle" fill="{sub_ink}" font-size="16">{lab}</text>')
    return out


def _line(labels, series, x0, y0, w, h, vmax, ybase, palette, sub_ink):
    out = []
    n = len(labels)
    if n < 2:
        return _bars(labels, series, x0, y0, w, h, vmax, ybase, palette, sub_ink)
    step = w / (n - 1)
    for si, (name, vals) in enumerate(series.items()):
        c = palette[si % len(palette)]
        pts = []
        for i in range(n):
            v = vals[i] if i < len(vals) and vals[i] is not None else 0
            pts.append(f"{x0 + i*step:.1f},{ybase-(v/vmax)*h:.1f}")
        out.append(f'<polyline points="{" ".join(pts)}" fill="none" stroke="{c}" stroke-width="4" stroke-linejoin="round"/>')
        for p in pts:
            xx, yy = p.split(",")
            out.append(f'<circle cx="{xx}" cy="{yy}" r="5" fill="{c}"/>')
    for i, lab in enumerate(labels):
        out.append(f'<text x="{x0+i*step:.1f}" y="{ybase+26}" text-anchor="middle" fill="{sub_ink}" font-size="16">{escape(str(lab))}</text>')
    return out
