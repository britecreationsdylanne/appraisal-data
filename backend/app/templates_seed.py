"""Seed report templates shipped with the tool. A template `spec` is a list of
sections the report runner knows how to execute. Section kinds:

  callout         : one metric over the whole range  -> value + n
  metric_over_time: a metric by granularity, optional split_by dimension
  breakdown       : a metric (usually count) grouped by a dimension, optional split_by
  split_share     : share of a dimension's values over time
"""
from sqlalchemy import select

from .models import SavedTemplate

LAB_VS_NATURAL = {
    "attributes": ["largest_diamond_source", "color_band", "clarity_band", "shape",
                   "carat_band", "generation", "briteco_category"],
    "sections": [
        {"title": "Total Pieces", "kind": "callout", "metric": "piece_count"},
        {"title": "Average Appraised Value", "kind": "callout", "metric": "avg_appraised_value"},
        {"title": "Natural vs Lab-Grown Share Over Time", "kind": "split_share",
         "dimension": "largest_diamond_source"},
        {"title": "Engagement Ring Lab-Grown Share Over Time", "kind": "split_share",
         "dimension": "largest_diamond_source", "filters": {"briteco_category": "Engagement Ring"}},
        {"title": "Non-Engagement Lab-Grown Share Over Time", "kind": "split_share",
         "dimension": "largest_diamond_source",
         "filters": {"briteco_category": {"op": "ne", "value": "Engagement Ring"}}},
        {"title": "Avg Appraised Value: Color × Clarity (Natural)", "kind": "breakdown_2d",
         "dim_a": "color_band", "dim_b": "clarity_band", "metric": "avg_appraised_value",
         "filters": {"largest_diamond_source": "natural"}},
        {"title": "Avg Appraised Value: Color × Clarity (Lab-Grown)", "kind": "breakdown_2d",
         "dim_a": "color_band", "dim_b": "clarity_band", "metric": "avg_appraised_value",
         "filters": {"largest_diamond_source": "lab"}},
        {"title": "Average Appraised Value — Natural vs Lab", "kind": "metric_over_time",
         "metric": "avg_appraised_value", "split_by": "largest_diamond_source"},
        {"title": "Average Carat — Natural vs Lab", "kind": "metric_over_time",
         "metric": "avg_carat", "split_by": "largest_diamond_source"},
        {"title": "Engagement Ring Avg Price — Natural vs Lab", "kind": "metric_over_time",
         "metric": "avg_sales_price", "split_by": "largest_diamond_source",
         "filters": {"briteco_category": "Engagement Ring"}},
        {"title": "Average Melee Weight — Natural vs Lab", "kind": "metric_over_time",
         "metric": "avg_melee_weight", "split_by": "largest_diamond_source"},
        {"title": "Diamond Color — Natural vs Lab", "kind": "breakdown",
         "dimension": "color_band", "split_by": "largest_diamond_source"},
        {"title": "Diamond Clarity — Natural vs Lab", "kind": "breakdown",
         "dimension": "clarity_band", "split_by": "largest_diamond_source"},
        {"title": "Avg Appraised Value by Color — Natural vs Lab", "kind": "breakdown",
         "dimension": "color_band", "metric": "avg_appraised_value", "split_by": "largest_diamond_source"},
        {"title": "Avg Appraised Value by Clarity — Natural vs Lab", "kind": "breakdown",
         "dimension": "clarity_band", "metric": "avg_appraised_value", "split_by": "largest_diamond_source"},
        {"title": "Shape Mix — Natural vs Lab", "kind": "breakdown",
         "dimension": "shape", "split_by": "largest_diamond_source"},
        {"title": "Carat Band Mix — Natural vs Lab", "kind": "breakdown",
         "dimension": "carat_band", "split_by": "largest_diamond_source"},
        {"title": "Category — Count Mix", "kind": "breakdown",
         "dimension": "briteco_category", "metric": "piece_count"},
        {"title": "Category — Value Mix", "kind": "breakdown",
         "dimension": "briteco_category", "metric": "total_appraised_value"},
        {"title": "Metal Mix", "kind": "breakdown", "dimension": "metal", "metric": "piece_count"},
        {"title": "Metal Grade Mix", "kind": "breakdown", "dimension": "metal_grade", "metric": "piece_count"},
        {"title": "Type & Style Mix", "kind": "breakdown", "dimension": "type_and_style", "metric": "piece_count"},
        {"title": "Fancy Color Mix", "kind": "breakdown", "dimension": "fancy_color", "metric": "piece_count"},
        {"title": "Fancy Intensity Mix", "kind": "breakdown", "dimension": "fancy_intensity", "metric": "piece_count"},
        {"title": "Gemstone Type Mix", "kind": "breakdown", "dimension": "largest_gemstone_type", "metric": "piece_count"},
        {"title": "Gemstone Quality", "kind": "breakdown", "dimension": "gemstone_quality", "metric": "piece_count"},
        {"title": "Lab-Grown Share by State", "kind": "geo", "mode": "share",
         "dimension": "largest_diamond_source", "value": "lab"},
        {"title": "Generation Split — Natural vs Lab", "kind": "breakdown",
         "dimension": "generation", "split_by": "largest_diamond_source"},
        {"title": "Avg Sales Price by Generation — Natural vs Lab", "kind": "breakdown",
         "dimension": "generation", "metric": "avg_sales_price", "split_by": "largest_diamond_source"},
    ],
}

GENERAL_SUMMARY = {
    "attributes": ["briteco_category", "metal"],
    "sections": [
        {"title": "Total Pieces", "kind": "callout", "metric": "piece_count"},
        {"title": "Total Appraised Value", "kind": "callout", "metric": "total_appraised_value"},
        {"title": "Average Appraised Value", "kind": "callout", "metric": "avg_appraised_value"},
        {"title": "Average Carat", "kind": "callout", "metric": "avg_carat"},
        {"title": "Pieces Over Time", "kind": "metric_over_time", "metric": "piece_count"},
        {"title": "Category Mix", "kind": "breakdown", "dimension": "briteco_category",
         "metric": "piece_count"},
        {"title": "Metal Mix", "kind": "breakdown", "dimension": "metal", "metric": "piece_count"},
    ],
}

WATCH_REPORT = {
    "table": "watches",  # all sections run against the watches table
    "attributes": ["brand", "movement", "case_material", "complication", "condition"],
    "sections": [
        {"title": "Total Watches", "kind": "callout", "metric": "piece_count"},
        {"title": "Average Appraised Value", "kind": "callout", "metric": "avg_appraised_value"},
        {"title": "Average Sales Price", "kind": "callout", "metric": "avg_sales_price"},
        {"title": "Average Appraised Value Over Time", "kind": "metric_over_time",
         "metric": "avg_appraised_value"},
        {"title": "Brand Mix", "kind": "breakdown", "dimension": "brand", "metric": "piece_count"},
        {"title": "Average Value by Brand", "kind": "breakdown", "dimension": "brand",
         "metric": "avg_appraised_value"},
        {"title": "Movement Mix", "kind": "breakdown", "dimension": "movement", "metric": "piece_count"},
        {"title": "Case Material Mix", "kind": "breakdown", "dimension": "case_material", "metric": "piece_count"},
        {"title": "Complication Mix", "kind": "breakdown", "dimension": "complication", "metric": "piece_count"},
        {"title": "Condition Mix", "kind": "breakdown", "dimension": "condition", "metric": "piece_count"},
        {"title": "Generation Mix", "kind": "breakdown", "dimension": "generation", "metric": "piece_count"},
        {"title": "Average Value by State", "kind": "geo", "mode": "metric", "metric": "avg_appraised_value"},
    ],
}

SEEDS = [
    ("Lab-Grown vs Natural Diamond Report",
     "The flagship annual report. Replicates every cut from the current dashboards.",
     LAB_VS_NATURAL),
    ("General Summary",
     "Always-on headline numbers: piece count, value, mix.",
     GENERAL_SUMMARY),
    ("Watch Report",
     "Watch appraisals by brand, movement, case material, complication, and condition.",
     WATCH_REPORT),
]


def seed_templates(session) -> None:
    """Upsert the shipped templates. Existing seed templates are refreshed to the
    latest definition on every startup; user-created templates are left alone."""
    existing = {t.name: t for t in session.execute(select(SavedTemplate)).scalars().all()}
    names = {name for name, _, _ in SEEDS}
    for name, desc, spec in SEEDS:
        t = existing.get(name)
        if t is None:
            session.add(SavedTemplate(name=name, description=desc, is_seed=True, spec=spec,
                                      owner="system", shared=True))
        elif t.is_seed:
            t.description = desc
            t.spec = spec
            t.owner = "system"
            t.shared = True
    # Prune renamed/removed official templates (leave user copies alone).
    for t in existing.values():
        if t.is_seed and t.name not in names:
            session.delete(t)
