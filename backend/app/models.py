from datetime import datetime

from sqlalchemy import (
    Date,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .db import AppraisalBase, AppBase


class Appraisal(AppraisalBase):
    """One appraised jewelry piece. Denormalized to mirror the BriteCo dashboards
    and the jewelry-appraisal-expert field vocabulary."""

    __tablename__ = "appraisals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Time
    appraisal_date: Mapped[Date] = mapped_column(Date, index=True)
    appraisal_year: Mapped[int] = mapped_column(Integer, index=True)
    year_quarter: Mapped[str] = mapped_column(String(8), index=True)  # e.g. "2024 Q3"

    # Piece taxonomy
    briteco_category: Mapped[str] = mapped_column(String(48), index=True)
    jewelry_type: Mapped[str] = mapped_column(String(48), index=True)
    piece_style: Mapped[str] = mapped_column(String(48))
    type_and_style: Mapped[str] = mapped_column(String(96))

    # Largest diamond
    largest_diamond_source: Mapped[str] = mapped_column(String(16), index=True)  # natural / lab
    shape: Mapped[str] = mapped_column(String(24), index=True)
    color_band: Mapped[str] = mapped_column(String(8))   # D-F / G-H / I-J / K-M / N-Z
    clarity_band: Mapped[str] = mapped_column(String(8))  # IF/FL / VVS / VS / SI / I
    largest_diamond_weight: Mapped[float] = mapped_column(Float)
    carat_band: Mapped[str] = mapped_column(String(16), index=True)
    melee_diamond_total_weight: Mapped[float] = mapped_column(Float, default=0.0)

    # Fancy / gemstone
    is_fancy: Mapped[bool] = mapped_column(default=False)
    fancy_color: Mapped[str] = mapped_column(String(24), nullable=True)
    fancy_intensity: Mapped[str] = mapped_column(String(24), nullable=True)
    largest_gemstone_type: Mapped[str] = mapped_column(String(32), nullable=True)
    gemstone_quality: Mapped[str] = mapped_column(String(8), nullable=True)

    # Mounting / brand / setting
    metal: Mapped[str] = mapped_column(String(24))
    metal_grade: Mapped[str] = mapped_column(String(16))
    setting: Mapped[str] = mapped_column(String(24))
    brand_name: Mapped[str] = mapped_column(String(32), default="no_brand")

    # Value
    sales_price: Mapped[float] = mapped_column(Float)
    replacement_value: Mapped[float] = mapped_column(Float)  # appraised value

    # Customer
    generation: Mapped[str] = mapped_column(String(16), index=True)
    customer_state: Mapped[str] = mapped_column(String(2), index=True)


class SavedTemplate(AppBase):
    """A re-runnable report definition (attributes + metrics + visuals)."""

    __tablename__ = "saved_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    is_seed: Mapped[bool] = mapped_column(default=False)  # shipped "Official" (locked)
    owner: Mapped[str] = mapped_column(String(120), default="system", index=True)
    shared: Mapped[bool] = mapped_column(default=False, index=True)
    spec: Mapped[dict] = mapped_column(JSONB)  # {attributes, metrics, sections}
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    created_by: Mapped[str] = mapped_column(String(120), default="local")


class ChatLog(AppBase):
    """A saved Chat question + its answer, so the user has a history like Reports."""

    __tablename__ = "chat_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner: Mapped[str] = mapped_column(String(120), default="local", index=True)
    shared: Mapped[bool] = mapped_column(default=False, index=True)
    question: Mapped[str] = mapped_column(String(500))
    answer: Mapped[str] = mapped_column(Text)
    metric: Mapped[str] = mapped_column(String(64), nullable=True)
    n: Mapped[int] = mapped_column(Integer, default=0)
    confidence: Mapped[str] = mapped_column(String(24), default="")
    caveat: Mapped[str] = mapped_column(Text, default="")
    plan: Mapped[dict] = mapped_column(JSONB, nullable=True)
    date_start: Mapped[Date] = mapped_column(Date)
    date_end: Mapped[Date] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class ReportRun(AppBase):
    """A dated execution of a template — preserved for year-over-year comparison."""

    __tablename__ = "report_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    template_id: Mapped[int] = mapped_column(Integer, index=True)
    template_name: Mapped[str] = mapped_column(String(120))
    owner: Mapped[str] = mapped_column(String(120), default="local", index=True)
    shared: Mapped[bool] = mapped_column(default=False, index=True)
    date_start: Mapped[Date] = mapped_column(Date)
    date_end: Mapped[Date] = mapped_column(Date)
    granularity: Mapped[str] = mapped_column(String(12), default="quarter")
    fact_pack: Mapped[dict] = mapped_column(JSONB)        # raw facts w/ n + caveats
    analysis: Mapped[dict] = mapped_column(JSONB, nullable=True)  # souls output (optional)
    analyzed: Mapped[bool] = mapped_column(default=False)
    run_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    run_by: Mapped[str] = mapped_column(String(120), default="local")


class Watch(AppraisalBase):
    """Synthetic watch appraisals — mirrors the diamond table's shape so the
    Watch Report works today. Swaps out for the real watch dataset later."""

    __tablename__ = "watches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    appraisal_date: Mapped[Date] = mapped_column(Date, index=True)
    appraisal_year: Mapped[int] = mapped_column(Integer, index=True)
    year_quarter: Mapped[str] = mapped_column(String(8), index=True)

    brand: Mapped[str] = mapped_column(String(40), index=True)
    movement: Mapped[str] = mapped_column(String(24))
    case_material: Mapped[str] = mapped_column(String(32))
    complication: Mapped[str] = mapped_column(String(32))
    condition: Mapped[str] = mapped_column(String(24))
    case_size_mm: Mapped[float] = mapped_column(Float)

    sales_price: Mapped[float] = mapped_column(Float)
    replacement_value: Mapped[float] = mapped_column(Float)

    generation: Mapped[str] = mapped_column(String(16), index=True)
    customer_state: Mapped[str] = mapped_column(String(2), index=True)


class SavedItem(AppBase):
    """Generic per-user saved history for Trends runs and exported Images."""

    __tablename__ = "saved_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    kind: Mapped[str] = mapped_column(String(16), index=True)  # "trend" | "image"
    owner: Mapped[str] = mapped_column(String(120), default="local", index=True)
    shared: Mapped[bool] = mapped_column(default=False, index=True)
    title: Mapped[str] = mapped_column(String(200))
    summary: Mapped[str] = mapped_column(Text, default="")
    payload: Mapped[dict] = mapped_column(JSONB)  # enough to re-run / re-render
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
