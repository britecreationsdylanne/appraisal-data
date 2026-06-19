"""Synthetic appraisal data with realistic, baked-in trends so the tool has
something honest to analyze before the real Postgres is connected.

Run:  python -m app.seed.generate
"""
from __future__ import annotations

import datetime as dt

import numpy as np
import pandas as pd
from sqlalchemy import text

from ..config import get_settings
from ..db import Base, SessionLocal, engine
from ..templates_seed import seed_templates
from .. import models  # noqa: F401  (register tables)

settings = get_settings()

# ---- distributions -------------------------------------------------------
YEAR_WEIGHTS = {2019: .07, 2020: .10, 2021: .14, 2022: .16, 2023: .17, 2024: .18, 2025: .18}

CATEGORY_W = {
    "Engagement Ring": .47, "Wedding Band": .158, "Other Ring": .145, "Earrings": .087,
    "Pendant": .05, "Bracelet": .046, "Necklace": .04, "Other": .004,
}

# lab-grown share by year — engagement rings adopt faster than everything else
ERING_LAB = {2019: .063, 2020: .191, 2021: .269, 2022: .349, 2023: .416, 2024: .466, 2025: .496}
OTHER_LAB = {2019: .025, 2020: .059, 2021: .094, 2022: .130, 2023: .175, 2024: .201, 2025: .218}

# average largest-diamond carat rises for lab, roughly flat for natural
LAB_CARAT = {2019: .9, 2020: 1.1, 2021: 1.3, 2022: 1.55, 2023: 1.8, 2024: 2.05, 2025: 2.25}
NAT_CARAT = {2019: 1.03, 2020: 1.05, 2021: 1.09, 2022: 1.16, 2023: 1.22, 2024: 1.27, 2025: 1.29}

COLOR_LAB = {"D-F": .709, "G-H": .228, "I-J": .05, "K-M": .009, "N-Z": .004}
COLOR_NAT = {"G-H": .445, "I-J": .254, "D-F": .238, "K-M": .056, "N-Z": .007}
CLAR_LAB = {"VS": .619, "VVS": .276, "SI": .09, "IF/FL": .011, "I": .004}
CLAR_NAT = {"SI": .46, "VS": .325, "I": .12, "VVS": .085, "IF/FL": .01}

SHAPE_W = {"Round": .505, "Oval": .116, "Princess": .077, "Emerald": .06, "Cushion": .054,
           "Marquise": .052, "Pear": .046, "Radiant": .05, "Asscher": .02, "Heart": .01, "Other": .03}
GEN_W = {"Millennial": .505, "Gen Z": .275, "Gen X": .126, "Baby Boomers": .092,
         "Silent": .0015, "Gen Alpha": .0005}
METAL_W = {"white_gold": .55, "yellow_gold": .274, "platinum": .119, "rose_gold": .05, "no_metal": .007}
GRADE_W = {"fourteen_k": .66, "eighteen_k": .15, "950": .12, "ten_k": .05, "22k": .01, "24k": .005, "no_grade": .005}
SETTING_W = {"prong": .55, "pave": .2, "bezel": .1, "channel": .08, "scallop": .04, "other_setting": .03}
BRAND_W = {"no_brand": .95, "cartier": .012, "tiffany": .01, "tacori": .008, "verragio": .007,
           "hearts_on_fire": .005, "david_yurman": .004, "van_cleef_arpels": .002, "other_brand": .002}
FANCY_COLOR_W = {"Yellow": .413, "Black": .14, "Blue": .133, "Brown": .093, "Pink": .058,
                 "Brown/ish Yellow": .049, "Gray": .042, "Green": .03, "Salt & Pepper": .025, "Other": .017}
FANCY_INT_W = {"Fancy": .472, "Fancy Light": .142, "Fancy Intense": .125, "Fancy Vivid": .086,
               "Fancy Deep": .05, "Light": .047, "Fancy Dark": .043, "Faint": .025, "Very Light": .01}
GEM_W = {"Sapphire - Blue": .2, "Emerald": .104, "Moissanite": .09, "Ruby": .074, "Tanzanite": .062,
         "Topaz - Blue": .05, "Amethyst": .045, "Aquamarine": .04, "Opal - White": .035,
         "Sapphire - Green": .03, "Morganite": .03, "Sapphire - Pink": .03, "Other": .21}
GEMQ_W = {"AAA": .62, "AA": .29, "A": .07, "B": .02}
STATES = ["CA", "TX", "FL", "NY", "IL", "PA", "OH", "GA", "NC", "MI", "NJ", "VA", "WA",
          "AZ", "MA", "TN", "IN", "MO", "MD", "WI", "CO", "MN", "SC", "AL", "LA", "OR"]

ENG_STYLES = ["ring_solitaire", "ring_halo", "ring_three_stone", "ring_pave", "ring_classic", "ring_contemporary"]
STYLE_LABEL = {"ring_solitaire": "Solitaire", "ring_halo": "Halo", "ring_three_stone": "Stone",
               "ring_pave": "Pave", "ring_classic": "Classic", "ring_contemporary": "Contemporary"}


def _choice(rng, weights: dict, n: int):
    keys = list(weights.keys())
    p = np.array(list(weights.values()), dtype=float)
    p = p / p.sum()
    return rng.choice(keys, size=n, p=p)


def _carat_band(c: float) -> str:
    edges = [(.5, "0.00-0.50"), (1, "0.50-1.00"), (1.5, "1.00-1.50"), (2, "1.50-2.00"),
             (2.5, "2.00-2.50"), (3, "2.50-3.00"), (4, "3.00-4.00")]
    for hi, label in edges:
        if c < hi:
            return label
    return ">4.00"


def build_frame(n: int) -> pd.DataFrame:
    rng = np.random.default_rng()
    years = _choice(rng, YEAR_WEIGHTS, n).astype(int)
    quarters = np.where(years == 2025, rng.integers(1, 3, n), rng.integers(1, 5, n))
    months = (quarters - 1) * 3 + rng.integers(1, 4, n)
    days = rng.integers(1, 29, n)
    dates = [dt.date(int(y), int(m), int(d)) for y, m, d in zip(years, months, days)]

    category = _choice(rng, CATEGORY_W, n)
    is_ering = category == "Engagement Ring"

    p_lab = np.array([ERING_LAB[y] if e else OTHER_LAB[y] for y, e in zip(years, is_ering)])
    source = np.where(rng.random(n) < p_lab, "lab", "natural")
    is_lab = source == "lab"

    # carat by source/year
    carat = np.empty(n)
    for i in range(n):
        mean = (LAB_CARAT if is_lab[i] else NAT_CARAT)[int(years[i])]
        carat[i] = max(0.18, rng.gamma(shape=6.0, scale=mean / 6.0))
    carat = np.round(carat, 2)

    # color/clarity by source
    color = np.where(is_lab, _choice(rng, COLOR_LAB, n), _choice(rng, COLOR_NAT, n))
    clarity = np.where(is_lab, _choice(rng, CLAR_LAB, n), _choice(rng, CLAR_NAT, n))

    shape = _choice(rng, SHAPE_W, n)

    # value: driven by carat, source premium (natural higher), category, year drift
    cat_factor = pd.Series(category).map({
        "Engagement Ring": 1.0, "Wedding Band": .45, "Other Ring": .6, "Earrings": .7,
        "Pendant": .55, "Bracelet": .8, "Necklace": .9, "Other": .5}).to_numpy()
    source_premium = np.where(is_lab, 1.0, 1.9)            # natural commands a premium
    lab_year_drift = np.array([1.0 - (y - 2019) * 0.05 for y in years])  # lab prices soften
    nat_year_drift = np.array([1.0 + (y - 2019) * 0.02 for y in years])
    year_drift = np.where(is_lab, lab_year_drift, nat_year_drift)
    base = np.power(carat, 1.35) * 5200 * cat_factor * source_premium * year_drift
    noise = rng.lognormal(mean=0.0, sigma=0.28, size=n)
    replacement_value = np.round(base * noise, 2)
    replacement_value = np.clip(replacement_value, 150, 250000)
    sales_price = np.round(replacement_value * rng.uniform(0.82, 0.96, n), 2)

    melee = np.round(np.clip(rng.gamma(2.0, 0.18, n), 0, 3.5), 2)

    generation = _choice(rng, GEN_W, n)
    state = rng.choice(STATES, size=n)
    metal = _choice(rng, METAL_W, n)
    grade = _choice(rng, GRADE_W, n)
    setting = _choice(rng, SETTING_W, n)
    brand = _choice(rng, BRAND_W, n)

    # fancy diamonds (~3%)
    is_fancy = rng.random(n) < 0.03
    fancy_color = np.where(is_fancy, _choice(rng, FANCY_COLOR_W, n), None)
    fancy_int = np.where(is_fancy, _choice(rng, FANCY_INT_W, n), None)

    # gemstone pieces (~9%)
    has_gem = rng.random(n) < 0.09
    gem_type = np.where(has_gem, _choice(rng, GEM_W, n), None)
    gem_q = np.where(has_gem, _choice(rng, GEMQ_W, n), None)

    # taxonomy
    jt_map = {"Engagement Ring": "ring_engagement", "Wedding Band": "ring_wedding",
              "Other Ring": "ring_fashion", "Earrings": "earrings", "Pendant": "pendant",
              "Bracelet": "bracelet", "Necklace": "necklace", "Other": "other"}
    jewelry_type = pd.Series(category).map(jt_map).to_numpy()
    piece_style = np.where(is_ering, rng.choice(ENG_STYLES, size=n),
                           pd.Series(category).map({
                               "Wedding Band": "anniversary", "Other Ring": "fashion",
                               "Earrings": "stud", "Bracelet": "tennis", "Pendant": "fashion",
                               "Necklace": "fashion", "Other": "fashion"}).fillna("fashion").to_numpy())
    type_and_style = np.where(
        is_ering,
        np.array([f"Engagement - {STYLE_LABEL.get(s, 'Classic')}" for s in piece_style]),
        np.array([f"{c} - All" for c in category]),
    )

    df = pd.DataFrame({
        "appraisal_date": dates,
        "appraisal_year": years,
        "year_quarter": [f"{y} Q{q}" for y, q in zip(years, quarters)],
        "briteco_category": category,
        "jewelry_type": jewelry_type,
        "piece_style": piece_style,
        "type_and_style": type_and_style,
        "largest_diamond_source": source,
        "shape": shape,
        "color_band": color,
        "clarity_band": clarity,
        "largest_diamond_weight": carat,
        "carat_band": [_carat_band(c) for c in carat],
        "melee_diamond_total_weight": melee,
        "is_fancy": is_fancy,
        "fancy_color": fancy_color,
        "fancy_intensity": fancy_int,
        "largest_gemstone_type": gem_type,
        "gemstone_quality": gem_q,
        "metal": metal,
        "metal_grade": grade,
        "setting": setting,
        "brand_name": brand,
        "sales_price": sales_price,
        "replacement_value": replacement_value,
        "generation": generation,
        "customer_state": state,
    })
    return df


# ---- watches -------------------------------------------------------------
WATCH_BRAND = {"Rolex": .26, "Omega": .14, "Cartier": .10, "TAG Heuer": .08, "Seiko": .06,
               "Tudor": .06, "Breitling": .05, "Tissot": .05, "Patek Philippe": .04,
               "Audemars Piguet": .03, "Jaeger-LeCoultre": .03, "Longines": .03, "Other": .07}
WATCH_BASE = {"Patek Philippe": 38000, "Audemars Piguet": 32000, "Rolex": 13000, "Jaeger-LeCoultre": 9000,
              "Cartier": 7000, "Omega": 6000, "Breitling": 5000, "Tudor": 4000, "TAG Heuer": 3500,
              "Longines": 1800, "Tissot": 800, "Seiko": 600, "Other": 2200}
WATCH_MOVE = {"Automatic": .68, "Quartz": .22, "Manual": .07, "Mechanical": .03}
WATCH_MAT = {"Stainless Steel": .55, "Two-Tone": .12, "Yellow Gold": .10, "Rose Gold": .07,
             "White Gold": .05, "Titanium": .05, "Platinum": .03, "Ceramic": .03}
WATCH_COMP = {"Date": .40, "Chronograph": .22, "None": .15, "Dive/Rotating Bezel": .05,
              "GMT": .08, "Moonphase": .06, "Perpetual Calendar": .04}
WATCH_COND = {"New": .20, "Like New": .28, "Excellent": .30, "Good": .15, "Fair": .04, "Vintage": .03}
WATCH_COND_F = {"New": 1.0, "Like New": .95, "Excellent": .88, "Good": .78, "Fair": .62, "Vintage": 1.15}


def build_watch_frame(n: int) -> pd.DataFrame:
    rng = np.random.default_rng()
    years = _choice(rng, YEAR_WEIGHTS, n).astype(int)
    quarters = np.where(years == 2025, rng.integers(1, 3, n), rng.integers(1, 5, n))
    months = (quarters - 1) * 3 + rng.integers(1, 4, n)
    days = rng.integers(1, 29, n)
    dates = [dt.date(int(y), int(m), int(d)) for y, m, d in zip(years, months, days)]

    brand = _choice(rng, WATCH_BRAND, n)
    cond = _choice(rng, WATCH_COND, n)
    base = pd.Series(brand).map(WATCH_BASE).to_numpy()
    cf = pd.Series(cond).map(WATCH_COND_F).to_numpy()
    year_drift = np.array([1.0 + (y - 2019) * 0.03 for y in years])
    noise = rng.lognormal(mean=0.0, sigma=0.30, size=n)
    replacement_value = np.round(np.clip(base * cf * year_drift * noise, 150, 400000), 2)
    sales_price = np.round(replacement_value * rng.uniform(0.82, 0.95, n), 2)
    case_size = np.round(np.clip(rng.normal(40, 3.2, n), 26, 46), 1)

    return pd.DataFrame({
        "appraisal_date": dates,
        "appraisal_year": years,
        "year_quarter": [f"{y} Q{q}" for y, q in zip(years, quarters)],
        "brand": brand,
        "movement": _choice(rng, WATCH_MOVE, n),
        "case_material": _choice(rng, WATCH_MAT, n),
        "complication": _choice(rng, WATCH_COMP, n),
        "condition": cond,
        "case_size_mm": case_size,
        "sales_price": sales_price,
        "replacement_value": replacement_value,
        "generation": _choice(rng, GEN_W, n),
        "customer_state": rng.choice(STATES, size=n),
    })


def seed_watches_if_empty(n: int = 18000) -> int:
    """Insert synthetic watches only if the table is empty (non-destructive)."""
    Base.metadata.create_all(engine)
    with engine.connect() as c:
        existing = c.execute(text("SELECT COUNT(*) FROM watches")).scalar()
    if existing:
        return int(existing)
    build_watch_frame(n).to_sql("watches", engine, if_exists="append", index=False,
                                chunksize=5000, method="multi")
    with engine.connect() as c:
        return int(c.execute(text("SELECT COUNT(*) FROM watches")).scalar())


def run(n: int | None = None) -> int:
    n = n or settings.seed_rows
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    df = build_frame(n)
    df.to_sql("appraisals", engine, if_exists="append", index=False, chunksize=5000, method="multi")
    build_watch_frame(18000).to_sql("watches", engine, if_exists="append", index=False,
                                    chunksize=5000, method="multi")
    with SessionLocal() as s:
        seed_templates(s)
        s.commit()
    with engine.connect() as c:
        count = c.execute(text("SELECT COUNT(*) FROM appraisals")).scalar()
        wcount = c.execute(text("SELECT COUNT(*) FROM watches")).scalar()
    print(f"Seeded {count} appraisals + {wcount} watches + report templates.")
    return count


if __name__ == "__main__":
    run()
