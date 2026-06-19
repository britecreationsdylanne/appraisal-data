# Appraisal Data Research — Design Doc

> Project: **Appraisal Data Research**. Local ports: backend `8010`, frontend `5176`, Postgres `5436`.

A friendly front-end over the BriteCo jewelry-appraisal database that lets a **non-data, writing-focused user** pull trustworthy facts, spot real trends, run annual report templates, and export on-brand visuals — without writing SQL or over-claiming statistics.

---

## 1. The core problem we're solving

You have (a) a big Postgres database of appraisal data and (b) mapping/rules that explain how to read the tables. The hard part isn't querying — it's making the output **trustworthy and writer-ready**:

- A writer needs **facts they can cite**, not a SQL console.
- A writer must not say "Ovals are surging!" when it's actually the whole diamond category rising, or when the sample is 12 stones. **Significance honesty is a first-class feature, not a footnote.**
- The same report (Lab vs Natural) must run **identically every year** so numbers are comparable.

So the tool is really: **a governed query layer + an analyst/skeptic agent pipeline + a publishing surface (facts, narrative, visuals).**

---

## 2. Three entry points (the user-facing modes)

### Mode 1 — Chat ("ask the data")
Natural-language questions → read-only SQL → results → plain-language answer **with the sample size and a caveat line every time.**
- For ad-hoc blog stats ("what's the average appraised value of a 1ct lab oval in 2024?").
- Every answer shows: the number, **n**, the exact filter applied, and a confidence note.
- A **global date-range control** sits above the chat (see §3.5) and scopes every question by default; the user can also override the range in natural language.
- One-click "show the SQL" and "show the rows" for trust/auditing.
- "Pin to facts" — save an answer into a Facts Tray the writer collects for an article.

### Mode 2 — Trends ("is anything interesting here?")
Pick an **attribute** (from a friendly menu) + a **timeframe** → the tool auto-runs a standard battery and surfaces ranked, vetted findings.
- **The attribute menu is generated directly from the `jewelry-appraisal-expert` field vocabulary** (mapped through the semantic layer), so the writer selects only real, well-defined values. That covers, at minimum:
  - **Diamond shape** (Round, Oval, Princess, Emerald, Cushion, Marquise, Pear, Radiant, …)
  - **Source** (Natural vs Lab-Grown)
  - **Color** grade and **Clarity** grade (D-F / G-H / I-J / K-M / N-Z; IF/FL, VVS, VS, SI, I)
  - **Carat band** (0.00–0.50, … >4.00)
  - **Fancy color** (Yellow, Pink, Blue, …) and **intensity** (Fancy, Fancy Vivid, …)
  - **Gemstone type** (Sapphire-Blue, Emerald, Ruby, …) and **quality** (AAA/AA/A/B)
  - **Jewelry type / piece style** (ring_engagement, ring_solitaire, ring_halo, bridal_set, …)
  - **Metal & grade** (White Gold 14K, Platinum 950, …); **setting** (prong, bezel, pave, scallop, …)
  - **Brand** (luxury brands per the skill's allow-list)
  - Demographic/geo where present (generation, US state)
- Standard battery per attribute: volume over time, share-of-mix over time, avg appraised value over time, **vs. the parent baseline** (e.g. Oval vs all shapes), natural vs lab split where relevant.
- Output: a ranked list of "notable findings," each tagged **Strong / Directional / Not significant**, each with a caveat and the comparison it was measured against.
- This is where the skeptic agent earns its keep (see §4).

### Mode 3 — Reports & Templates ("build it once, run it every year")
A Template is a **versioned, re-runnable spec** of attributes + metrics + dimensions + visuals + narrative sections. Build a report, save it, and run it again later — including against **new dates** — without rebuilding.

**Build a custom report**
- Pick attributes (same `jewelry-appraisal-expert` vocabulary as Trends) + metrics + visuals.
- Preview against the current date range, then **Save as Template** for future reuse.

**Re-run & versioning (core requirement)**
- Open any saved template, change the date range, and **Run** — produces a fresh, dated run while keeping the template definition stable.
- **Save the run** so each year's output is preserved and comparable (e.g. 2024 run vs 2025 run of the same template).
- Templates are diff-able year over year ("Lab e-ring share went 46.6% → 49.59%").

**Saved-report history**
- A **History** view lists every saved template and every dated run beneath it (template name · date range · run date · who ran it).
- One click to re-open, re-run with new dates, duplicate, or compare two runs.

**Analyze ("run the souls")**
- An **Analyze** action on any report/run hands the fact pack to the agent pipeline (Analyst → Skeptic → Narrator, §4) to produce vetted findings + a plain-language insight summary on demand.
- Analyze is **optional and explicit** — the writer can pull raw facts only, or ask the souls to interpret them.

**Seed templates we ship**
- Flagship: **Lab-Grown vs Natural Diamond Report** (replicates every cut in your current dashboards — see §6).
- Planned: **Watch Report**, **General Summary** (piece count, total/average value, mix).
- Each run produces: a **fact pack** (every data point, with n + caveats), an optional **narrative draft of insights** (not the final article), and an **export set** of branded visuals.

---

## 3. The data & semantic layer (how we stay trustworthy)

The mapping/rules you'll provide become a **semantic layer** — the single source of truth that both the agents and the UI read. This is the most important architectural piece.

```
semantic_layer/
  dimensions.yaml   # friendly name -> column/filter (e.g. "Oval" -> shape = 'oval')
  metrics.yaml      # "avg appraised value" -> AVG(replacement_value), with grain rules
  rules.yaml        # the appraisal domain rules (melee threshold, lab/natural defaults, etc.)
  baselines.yaml    # what each attribute is compared against (Oval -> all shapes)
```

Why this matters:
- The SQL agent **only references columns/joins the semantic layer exposes** → no hallucinated tables, no wrong grain.
- The attribute picker in Trends is generated **from** `dimensions.yaml` → the writer always picks valid, well-defined things.
- Domain rules (e.g. melee = ≤0.18ct per stone, melee source defaults to natural, color "G-H" → from/to) live in one place and are applied consistently.

**Local-first plan:** we build now against a Postgres schema + synthetic seed data that mirrors the expected appraisal shape (informed by the jewelry-appraisal-expert fields and your dashboard dimensions). Swapping to your real DB later = point the connection at it + reconcile `dimensions/metrics.yaml` to the real column names. The app code doesn't change.

---

## 3.5 Date filtering is global (every mode, everywhere)

Time is the spine of almost every question here, so date controls are a **shared, first-class component**, not a per-page afterthought.

- A **global DateRange control** lives in the app shell and applies to Chat, Trends, Templates, and Export Studio.
- Supports: **presets** (This year, Last year, Last 4 quarters, Last 12 months, Year-to-date, All time), **custom start/end**, and **granularity** (day / month / quarter / year) so charts roll up correctly.
- The active range is part of the query context passed to the agents and is **stamped onto every fact, finding, and exported image** — a number can never be quoted without the period it covers.
- Date column comes from the semantic layer (e.g. `appraisal_year` / `year_quarter` as seen in the dashboards), so changing the underlying date field is one config edit.
- Individual modes can narrow further (e.g. Trends timeframe, Template "report year") but always inside the global range.

## 4. The agents ("souls") and their jobs

A deterministic stats core does the math (pandas/scipy); the LLM agents plan, interpret, and write. This keeps numbers reproducible and the prose honest.

| Agent | Job | Model | Notes |
|-------|-----|-------|-------|
| **Router** | Classify intent / pick the query template | Haiku 4.5 | Cheap, fast front door |
| **Query Planner** | NL + semantic layer → read-only SQL | Sonnet 4.6 (escalate to Fable 5 on complex/multi-join) | SQL is validated against an allow-list; read-only role |
| **Analyst** | Run results through the stats core: derived metrics, sample sizes, significance, trend slope + CI, slice-vs-baseline | Fable 5 (interprets) + Python (computes) | Math is code, not vibes |
| **Skeptic** | Adversarial pass: is this a real finding or noise / a broader trend / low-n? Forces a label | Fable 5 (independent context) | The over-claim guard. Defaults to skeptical |
| **Narrator** | Turn vetted findings into plain-language insight summary for the writer | Fable 5 | Facts + caveats + narrative — **not** the final article |

Model picks follow `model-migration` (frontier = Fable 5 / Opus 4.8, standard = Sonnet 4.6, economy = Haiku 4.5). We'll keep model IDs in config so `/update-models` can migrate them.

### Significance honesty — the hard rules the pipeline enforces
1. **Never report a stat without n.** Sample size travels with every number, everywhere.
2. **Minimum-n gate.** Below a configurable threshold → labeled "Directional, low confidence," never "Strong."
3. **Slice vs. baseline is mandatory.** Before claiming "Ovals are up," compare Oval's trend to the all-shapes trend. If the parent moved the same way, the finding is reframed as "part of a broader category trend," not an Oval-specific insight.
4. **Real significance tests.** Proportion z-tests for share shifts; regression slope + confidence interval for trends; flag when a "change" is within noise.
5. **No causal language** unless the data supports it; default to descriptive ("associated with," not "because of").
6. **Plain-English confidence chip** on every finding: 🟢 Strong / 🟡 Directional / ⚪ Not significant.

---

## 5. Visuals & infographics (both, per your answer)

Two consumers of the **same dataset object**, so a chart and its export never disagree:

- **Interactive (in-app):** Recharts, BriteCo-themed (teal `#008182` for emphasis, the dashboard palette for categories). For exploring and screenshotting.
- **Branded static exports ("Export Studio"):** compose chart + headline + stat callouts + logo into on-brand layouts, rendered server-side (headless Chromium) to PNG/SVG at preset sizes:
  - 1:1 (1080×1080 Instagram), 4:5 (1080×1350 IG portrait), 9:16 (1080×1920 story/Reel), 16:9 (blog/landscape), 2:3 (Pinterest). All configurable.
  - Gilroy type, solid colors (no gradients, per brand), light `#F4F7FC` or white backgrounds, orange CTA accents only where appropriate.
- Every exported image carries the **caption metadata** (timeframe, n, source) so a caveat can be added to alt-text/footnotes — no orphaned stats.

---

## 6. The Lab vs Natural template (build-first proof)

Encodes every cut visible in your current dashboards as named metrics/visuals so the revamp is a faithful-but-better replacement:

- Count vs Value mix by category (pie/donut pair)
- Natural vs Lab volume by year; price by carat-band
- Lab vs Natural **average carat** by quarter and by color grade
- E-ring price over time — lab vs natural, separately and indexed
- Color & clarity distribution — natural vs lab (side-by-side)
- Avg appraised value by color × clarity
- Fancy color & intensity distributions; gemstone quality (AAA/AA/A/B)
- Shape mix — natural vs lab
- **Lab-grown share over time** — e-rings vs other types (the headline trend)
- Metal type mix; type_and_style breakdown
- Generation split (Gen Z / Millennial / Gen X / Boomers) natural vs lab; US state map
- Summary callouts: total pieces, average value, YoY deltas

Each becomes a reusable metric in `metrics.yaml`, so Trends and Chat can reach the same definitions.

---

## 7. UI / layout (BriteCo-branded internal tool)

- **Shell:** left nav (navy `#272D3F`), page background frost `#F4F7FC`, white cards with `#E1E7EF` borders. Logo `logo-dark-bg-primary.svg` in nav.
- **Nav items:** Chat · Trends · Templates · Export Studio · Facts Tray.
- **Facts Tray** (persistent right rail or drawer): the writer's clipboard of pinned facts across modes — each with number, n, filter, caveat — exportable to the blog/report.
- **Confidence chips, sample-size badges, "show SQL/rows"** are global components reused everywhere.
- Tone in microcopy: optimistic, plain, "you/your," per brand voice.

---

## 8. Stack (matches your other BriteCo apps)

- **Backend:** FastAPI + Postgres. Python for the stats core (pandas/scipy) and Anthropic SDK agent orchestration.
- **Frontend:** React + TypeScript + Vite + Tailwind.
- **DB:** Postgres in Docker locally (port **5436** — 5432–5435 are taken by your social/parking/blog/shadow DBs). Cloud SQL in prod. **No SQLite** (per project rule).
- **Charts:** Recharts (interactive) + headless-Chromium render for branded exports.
- **Agents:** Anthropic SDK; model IDs in config.
- **Git/deploy:** you'll create the repo and hook up the real data; we build locally first.

---

## 9. Suggested build order (local)

1. **App shell + brand system + nav** (empty modes, Facts Tray).
2. **Semantic layer + synthetic Postgres seed** (so everything has data to hit).
3. **Stats core** (significance, baseline comparison, sample-size gating) — pure Python, unit-tested.
4. **Chat mode** end-to-end (Router → Planner → Analyst → answer w/ n + caveat).
5. **Trends mode** (attribute picker → battery → skeptic → ranked findings).
6. **Reports & Templates:** custom report builder → Save as Template → re-run with new dates → saved-run **History** → **Analyze** (run the souls). Persist templates + dated runs in Postgres. Ship the Lab vs Natural spec.
7. **Export Studio** (branded multi-size images).
8. Wire to real Postgres + **GCP/Cloud Run** deploy + git project; reconcile semantic layer to real columns.

---

## 10. Open questions before we build

1. Name — keep **BriteLens** or prefer another?
2. **General Summary** — which always-on numbers matter (piece count, total value, avg value, mix, YoY)? Anything else?
3. Audience for the deployed tool — just the content/writing team, or wider? (affects auth depth)
4. Any image sizes beyond IG/story/blog/Pinterest (e.g. email header, PDF report page)?
5. For Templates, do you want a human "approve the metric list" step before a run is publishable, or auto-run and let the writer prune?
