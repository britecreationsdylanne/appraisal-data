"""Loads and validates the semantic layer. Single source of truth for
friendly-name -> column mapping, metrics, baselines, and rules."""
from functools import lru_cache
from pathlib import Path

import yaml

_DIR = Path(__file__).parent


def _load(name: str) -> dict:
    with open(_DIR / name, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


@lru_cache
def dimensions() -> dict:
    return _load("dimensions.yaml")


@lru_cache
def metrics() -> dict:
    return _load("metrics.yaml")["metrics"]


@lru_cache
def rules() -> dict:
    return _load("rules.yaml")


def dimension(key: str) -> dict:
    dims = dimensions()["dimensions"]
    if key not in dims:
        raise KeyError(f"Unknown dimension '{key}'")
    return dims[key]


def baseline_filter(baseline_key: str) -> str | None:
    bl = dimensions().get("baselines", {}).get(baseline_key)
    return bl.get("filter") if bl else None


def attribute_menu() -> list[dict]:
    """Shape the dimensions for the Trends/Reports attribute picker UI."""
    dims = dimensions()["dimensions"]
    groups = {g["key"]: g["label"] for g in dimensions()["groups"]}
    out = []
    for key, d in dims.items():
        out.append(
            {
                "key": key,
                "label": d["label"],
                "group": groups.get(d.get("group", ""), d.get("group", "")),
                "values": d.get("values", []),
                "value_labels": d.get("value_labels", {}),
                "baseline": d.get("baseline"),
                "placeholder": d.get("placeholder", False),
                "needs_dataset": d.get("needs_dataset"),
            }
        )
    return out


# ---- safety: which columns may appear in a WHERE/GROUP BY ----
@lru_cache
def allowed_columns() -> set[str]:
    cols = {d["column"] for d in dimensions()["dimensions"].values() if d.get("column")}
    cols |= {
        "appraisal_date",
        "appraisal_year",
        "year_quarter",
        "is_fancy",
        "replacement_value",
        "sales_price",
        "largest_diamond_weight",
        "melee_diamond_total_weight",
        "generation",
        "customer_state",
        # watch table columns
        "brand",
        "movement",
        "case_material",
        "complication",
        "condition",
        "case_size_mm",
    }
    return cols
