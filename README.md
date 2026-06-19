# Appraisal Data Research

A friendly research tool over the BriteCo jewelry-appraisal database for a **non-data, writing-focused** user. Pull trustworthy facts, spot real trends, run annual report templates, and export on-brand visuals — without writing SQL or over-claiming statistics.

See **[DESIGN.md](DESIGN.md)** for the full design rationale.

## What it does

- **Chat** — ask in plain English; get a governed, read-only query answered **with sample size + caveat** every time.
- **Trends** — pick an attribute (Oval, Lab-Grown, Emerald…) + a timeframe; the "souls" run share/volume/value analysis, each labeled **Strong / Directional / Not significant** and compared to its baseline so you never over-claim.
- **Reports** — run saved templates (flagship: **Lab-Grown vs Natural**) for any date range, **save the dated run**, view **History**, build your own and **Save as Template**, and **Analyze** (run the souls) on demand.
- **Export Studio** — turn any trend into a BriteCo-branded image at IG / story / blog / Pinterest sizes (period + n baked into the footer).

Date filtering is **global** across every mode.

## Architecture

- **Backend:** FastAPI + Postgres + SQLAlchemy. Deterministic **stats core** (scipy) does all the math; the **souls** (Claude via the Anthropic SDK) only plan queries and interpret results. Without an API key they fall back to deterministic templates, so the tool is fully usable offline.
- **Semantic layer** (`backend/app/semantic/*.yaml`) is the single source of truth mapping friendly attribute names → columns, plus metrics, baselines, and the significance rules. Pointing at the real DB later = reconcile these column names; app code is unchanged.
- **Frontend:** React + TypeScript + Vite + Tailwind + Recharts, BriteCo-branded.

## Local ports

| Service | Port |
|---------|------|
| Postgres (Docker) | 5436 |
| Backend (FastAPI) | 8010 |
| Frontend (Vite) | 5176 |

## Run it

```bash
# 1. Postgres
docker compose up -d

# 2. Backend
cd backend
python -m venv venv
venv\Scripts\activate            # Windows (PowerShell: venv\Scripts\Activate.ps1)
pip install -r requirements.txt
copy .env.example .env           # optional: add ANTHROPIC_API_KEY to make the souls "live"
python -m app.seed.generate      # seeds 60k synthetic appraisals + report templates
uvicorn app.main:app --port 8010 --reload

# 3. Frontend (new terminal)
cd frontend
npm install
npm run dev
```

Open **http://localhost:5176**.

> The souls run in **offline fallback** mode until you set `ANTHROPIC_API_KEY` in `backend/.env`. All numbers and significance labels are identical either way — the key only makes the narrative more fluent.

## Connecting the real data (later)

1. Point `DATABASE_URL` in `backend/.env` at the real Postgres.
2. Reconcile `backend/app/semantic/dimensions.yaml` / `metrics.yaml` column names to the real schema.
3. Skip the synthetic seed. Everything else is unchanged.

## Project layout

```
backend/app/
  semantic/      # dimensions, metrics, rules (the trust-critical config)
  stats/core.py  # significance, baseline comparison, sample-size gating
  services/      # query builder, chat, trends, reports, analyze, export
  agents/souls.py# Claude planner/analyst/narrator (+ deterministic fallback)
  seed/          # synthetic data generator
  api/           # FastAPI routers
frontend/src/
  components/    # Shell, DateRangeControl, FactsTray, Chart, ConfidenceChip
  pages/         # Chat, Trends, Reports, ExportStudio
```
