import { useEffect, useState } from "react";
import { api } from "../api";
import { useApp } from "../state";
import Chart from "../components/Chart";
import USMap from "../components/USMap";
import ConfidenceChip, { NBadge } from "../components/ConfidenceChip";
import { fmtCurrency, fmtInt } from "../brand";
import { specFromSection } from "../exportHelpers";

type Tab = "templates" | "history" | "build";

export default function Reports() {
  const { range, user } = useApp();
  const [tab, setTab] = useState<Tab>("templates");
  const [templates, setTemplates] = useState<any[]>([]);
  const [runs, setRuns] = useState<any[]>([]);
  const [active, setActive] = useState<any>(null); // {fact_pack, analysis, meta}
  const [busy, setBusy] = useState(false);
  const [editing, setEditing] = useState<any>(null);

  const reload = async () => {
    setTemplates(await api.templates());
    setRuns(await api.runs());
  };
  useEffect(() => {
    reload();
  }, [user]); // runs are per-user; reload when the active user changes

  // template action helpers
  const rename = async (t: any) => {
    const name = window.prompt("Rename report", t.name);
    if (name && name !== t.name) { await api.updateTemplate(t.id, { name }); reload(); }
  };
  const toggleShareTpl = async (t: any) => { await api.shareTemplate(t.id, !t.shared); reload(); };
  const removeTpl = async (t: any) => { if (confirm(`Delete "${t.name}"?`)) { await api.deleteTemplate(t.id); reload(); } };
  const duplicateTpl = async (t: any) => { await api.duplicateTemplate(t.id); reload(); };

  async function runTemplate(t: any) {
    setBusy(true);
    try {
      const res = await api.runTemplate(t.id, range, true);
      setActive({ name: t.name, run_id: res.run_id, fact_pack: res.fact_pack, analysis: null });
      await reload();
    } finally {
      setBusy(false);
    }
  }

  async function openRun(r: any) {
    const full = await api.run(r.id);
    setActive({ name: full.template_name, run_id: full.id, fact_pack: full.fact_pack, analysis: full.analysis });
  }

  async function analyze() {
    if (!active?.run_id) return;
    setBusy(true);
    try {
      const a = await api.analyze(active.run_id);
      setActive({ ...active, analysis: a });
      await reload();
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <h1 className="text-2xl font-semibold mb-1">Reports — build once, run every year</h1>
      <p className="text-slate mb-4 max-w-3xl">
        Run a saved template against any date range, save the dated run, and let the souls analyze it.
        Build your own and save it as a template for next year.
      </p>

      <div className="flex gap-2 mb-4">
        {(["templates", "history", "build"] as Tab[]).map((t) => (
          <button
            key={t}
            className={`px-4 py-2 rounded-md font-semibold text-sm ${tab === t ? "bg-teal text-white" : "btn-ghost"}`}
            onClick={() => setTab(t)}
          >
            {t === "templates" ? "Templates" : t === "history" ? "History" : "Build new"}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
        <div className="lg:col-span-5 xl:col-span-4">
          {tab === "templates" && (
            <div className="space-y-5">
              <TemplateGroup
                title="Official templates" hint="Team-aligned. Locked — editing makes your own copy."
                items={templates.filter((t) => t.is_seed)}
                {...{ user, busy, runTemplate, setEditing, setTab, rename, toggleShareTpl, removeTpl, duplicateTpl }}
              />
              <TemplateGroup
                title="My reports" hint="Yours to edit, rename, share, and delete."
                items={templates.filter((t) => !t.is_seed && t.owner === user)}
                emptyText="None yet. Build one, or duplicate an official template."
                {...{ user, busy, runTemplate, setEditing, setTab, rename, toggleShareTpl, removeTpl, duplicateTpl }}
              />
              <TemplateGroup
                title="Shared library" hint="Shared by teammates. Run or duplicate."
                items={templates.filter((t) => !t.is_seed && t.shared && t.owner !== user)}
                emptyText="Nothing shared by others yet."
                {...{ user, busy, runTemplate, setEditing, setTab, rename, toggleShareTpl, removeTpl, duplicateTpl }}
              />
            </div>
          )}

          {tab === "history" && (
            <div className="space-y-2">
              <div className="text-xs text-slate mb-1">Your saved runs, private to <strong>{user}</strong>.</div>
              {!runs.length && <div className="text-sm text-slate">No saved runs yet.</div>}
              {runs.map((r) => (
                <div key={r.id} className="card p-3">
                  <button className="w-full text-left" onClick={() => openRun(r)}>
                    <div className="font-semibold text-sm">{r.template_name}</div>
                    <div className="text-xs text-slate mt-1">{r.date_start} → {r.date_end} · by {r.granularity}</div>
                    <div className="text-xs text-slate mt-1">
                      n={fmtInt(r.n_total)} · {r.analyzed ? "analyzed" : "not analyzed"} · {r.run_at?.slice(0, 16)}
                    </div>
                  </button>
                  <div className="flex gap-3 mt-2">
                    <button className="text-xs text-teal font-semibold" onClick={async () => { await api.shareRun(r.id, !r.shared); reload(); }}>
                      {r.shared ? "Unshare" : "Share"}
                    </button>
                    <button className="text-xs text-slate hover:text-coral" onClick={async () => { await api.deleteRun(r.id); if (active?.run_id === r.id) setActive(null); reload(); }}>
                      Delete
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}

          {tab === "build" && (
            <Builder
              editing={editing}
              onSaved={() => { reload(); setEditing(null); setTab("templates"); }}
              onCancel={() => setEditing(null)}
            />
          )}
        </div>

        <div className="lg:col-span-7 xl:col-span-8">
          {!active && <div className="card p-6 text-slate">Run a template or open a saved run to see the fact pack.</div>}
          {active && (
            <div>
              <div className="flex items-center justify-between mb-3">
                <div>
                  <div className="text-lg font-semibold">{active.name}</div>
                  <div className="text-xs text-slate">
                    {active.fact_pack.date_start} → {active.fact_pack.date_end} · n={fmtInt(active.fact_pack.n_total)}
                  </div>
                </div>
                <button className="btn-primary text-sm" onClick={analyze} disabled={busy || !active.run_id}>
                  {active.analysis ? "Re-analyze" : "Analyze (run the souls)"}
                </button>
              </div>

              {active.analysis && <Analysis a={active.analysis} />}

              <div className="space-y-4 mt-4">
                {active.fact_pack.sections.map((s: any, i: number) => (
                  <Section key={i} s={s} period={`${active.fact_pack.date_start} → ${active.fact_pack.date_end}`} />
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function TemplateGroup({ title, hint, items, emptyText, user, busy, runTemplate, setEditing, setTab,
                         rename, toggleShareTpl, removeTpl, duplicateTpl }: any) {
  return (
    <div>
      <div className="flex items-baseline justify-between">
        <h3 className="font-semibold text-navy">{title}</h3>
        <span className="text-xs text-slate">{items.length}</span>
      </div>
      <p className="text-xs text-slate mb-2">{hint}</p>
      {!items.length && emptyText && <div className="text-sm text-slate mb-2">{emptyText}</div>}
      <div className="space-y-2">
        {items.map((t: any) => {
          const mine = !t.is_seed && t.owner === user;
          const official = t.is_seed;
          return (
            <div key={t.id} className="card p-3">
              <div className="flex items-center justify-between gap-2">
                <div className="font-semibold">{t.name}</div>
                {official ? <span className="text-xs text-teal shrink-0">official</span>
                  : mine ? (t.shared && <span className="text-xs text-teal shrink-0">shared</span>)
                  : <span className="text-xs text-slate shrink-0">@{t.owner}</span>}
              </div>
              {t.description && <div className="text-xs text-slate mt-1">{t.description}</div>}
              <div className="text-xs text-slate mt-1">{t.spec?.sections?.length ?? 0} sections</div>
              <button className="btn-primary text-sm mt-2 w-full" disabled={busy} onClick={() => runTemplate(t)}>
                Run for current range
              </button>
              <div className="flex flex-wrap gap-x-3 gap-y-1 mt-2 text-xs">
                {(official || mine) && (
                  <button className="text-teal font-semibold" onClick={() => { setEditing(t); setTab("build"); }}>
                    {official ? "Edit (saves a copy)" : "Edit / add attributes"}
                  </button>
                )}
                <button className="text-teal font-semibold" onClick={() => duplicateTpl(t)}>Duplicate</button>
                {mine && <button className="text-teal font-semibold" onClick={() => rename(t)}>Rename</button>}
                {mine && <button className="text-teal font-semibold" onClick={() => toggleShareTpl(t)}>{t.shared ? "Unshare" : "Share"}</button>}
                {mine && <button className="text-slate hover:text-coral" onClick={() => removeTpl(t)}>Delete</button>}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function Analysis({ a }: { a: any }) {
  return (
    <div className="card p-4 border-l-4 border-teal">
      <div className="text-xs uppercase tracking-wide text-slate font-semibold">Souls' analysis {a.souls_live ? "(Claude)" : "(offline fallback)"}</div>
      <div className="text-navy mt-1">{a.narrative || a.summary}</div>
      <div className="grid grid-cols-2 gap-4 mt-3">
        <div>
          <div className="text-xs font-semibold text-teal mb-1">Safe to say</div>
          {a.safe_to_say?.length ? a.safe_to_say.map((s: string, i: number) => (
            <div key={i} className="text-sm text-steel">✓ {s}</div>
          )) : <div className="text-sm text-slate">Nothing rose above noise.</div>}
        </div>
        <div>
          <div className="text-xs font-semibold text-coral mb-1">Do not say</div>
          {a.do_not_say?.length ? a.do_not_say.map((s: string, i: number) => (
            <div key={i} className="text-sm text-slate">✕ {s}</div>
          )) : <div className="text-sm text-slate">—</div>}
        </div>
      </div>
    </div>
  );
}

function Section({ s, period }: { s: any; period: string }) {
  const { openExport } = useApp();
  if (s.kind === "note") return <div className="card p-4"><div className="font-semibold">{s.title}</div><div className="text-sm text-slate mt-1">{s.note}</div></div>;
  if (s.kind === "error") return <div className="card p-4 border-l-4 border-coral"><div className="font-semibold">{s.title}</div><div className="text-sm text-coral mt-1">{s.error}</div></div>;

  const d = s.data;
  const canExport = ["metric_over_time", "breakdown", "breakdown_2d", "split_share"].includes(s.kind);
  return (
    <div className="card p-4">
      <div className="flex items-center justify-between gap-2">
        <div className="font-semibold">{s.title}</div>
        <div className="flex items-center gap-2">
          {s.n != null && <NBadge n={s.n} />}
          {canExport && (
            <button
              className="text-xs text-teal font-semibold"
              onClick={() => {
                const spec = specFromSection(s, period);
                if (spec) openExport(spec);
              }}
            >
              Export image
            </button>
          )}
        </div>
      </div>
      {s.caveats?.map((c: string, i: number) => <div key={i} className="text-sm text-coral mt-1">⚠ {c}</div>)}

      {s.kind === "callout" && (
        <div className="text-3xl font-semibold text-teal mt-2">
          {d.label?.toLowerCase().includes("value") || d.label?.toLowerCase().includes("price")
            ? fmtCurrency(d.value)
            : d.label?.toLowerCase().includes("carat")
            ? d.value?.toFixed(2)
            : fmtInt(d.value)}
        </div>
      )}

      {s.kind === "metric_over_time" && (
        <div className="mt-3"><Chart kind="line" x={d.periods} series={d.series} /></div>
      )}

      {s.kind === "breakdown" && <Breakdown d={d} />}

      {s.kind === "breakdown_2d" && (
        <div className="mt-3"><Chart kind="bar" x={d.a_keys} series={d.series} /></div>
      )}

      {s.kind === "geo" && <USMap byState={d.by_state} min={d.min} max={d.max} mode={d.mode} label={d.label} />}

      {s.kind === "split_share" && <ShareChart d={d} />}
    </div>
  );
}

function Breakdown({ d }: { d: any }) {
  if (d.groups) {
    const keys = Array.from(new Set(Object.values(d.groups).flatMap((g: any) => g.map((x: any) => x.key))));
    const series: Record<string, (number | null)[]> = {};
    Object.entries(d.groups).forEach(([split, rows]: any) => {
      series[split] = keys.map((k) => rows.find((r: any) => r.key === k)?.value ?? 0);
    });
    return <div className="mt-3"><Chart kind="bar" x={keys as string[]} series={series} /></div>;
  }
  const items = (d.items || []);
  // Distributions (count / total value) read best as a donut, like the dashboards;
  // average metrics stay as bars (a pie of averages would be misleading).
  const isDistribution = d.metric === "piece_count" || d.metric === "total_appraised_value";
  if (isDistribution) {
    return <div className="mt-3"><Chart kind="pie" x={items.map((i: any) => i.key)} series={{ [d.label]: items.map((i: any) => i.value) }} /></div>;
  }
  const top = items.slice(0, 12);
  return <div className="mt-3"><Chart kind="bar" x={top.map((i: any) => i.key)} series={{ [d.label]: top.map((i: any) => i.value) }} /></div>;
}

function ShareChart({ d }: { d: any }) {
  const series: Record<string, number[]> = {};
  d.keys.forEach((k: string) => (series[k] = d.shares[k].map((v: number) => +(v * 100).toFixed(1))));
  return (
    <div className="mt-3">
      <Chart kind="line" x={d.periods} series={series} />
      <div className="flex flex-wrap gap-3 mt-2">
        {d.shift && Object.entries(d.shift).map(([k, sh]: any) => (
          <div key={k} className="text-xs flex items-center gap-1.5">
            <span className="font-semibold">{k}</span>
            <span className="text-slate">{sh.delta_pts > 0 ? "+" : ""}{sh.delta_pts} pts</span>
            <ConfidenceChip label={sh.label} />
          </div>
        ))}
      </div>
    </div>
  );
}

// ---- Builder -------------------------------------------------------------
function Builder({ onSaved, editing, onCancel }: { onSaved: () => void; editing?: any; onCancel?: () => void }) {
  const { meta } = useApp();
  const [name, setName] = useState("My custom report");
  const [desc, setDesc] = useState("");
  const [sections, setSections] = useState<any[]>([]);
  const [kind, setKind] = useState("callout");
  const [metric, setMetric] = useState("avg_appraised_value");
  const [dimension, setDimension] = useState("largest_diamond_source");
  const [split, setSplit] = useState(false);
  const [msg, setMsg] = useState("");

  useEffect(() => {
    if (editing) {
      setName(editing.name + (editing.is_seed ? " (edited)" : ""));
      setDesc(editing.description || "");
      setSections(editing.spec?.sections || []);
      setMsg("");
    }
  }, [editing]);

  const metrics = meta?.metrics || [];
  const attrs = (meta?.attributes || []).filter((a: any) => !a.placeholder);

  function addSection() {
    const title =
      kind === "callout" ? metrics.find((m: any) => m.key === metric)?.label
      : kind === "metric_over_time" ? `${metrics.find((m: any) => m.key === metric)?.label} over time`
      : kind === "breakdown" ? `${attrs.find((a: any) => a.key === dimension)?.label} breakdown`
      : `${attrs.find((a: any) => a.key === dimension)?.label} share over time`;
    const sec: any = { title, kind };
    if (kind === "callout" || kind === "metric_over_time") sec.metric = metric;
    if (kind === "breakdown" || kind === "split_share") sec.dimension = dimension;
    if (split && (kind === "metric_over_time" || kind === "breakdown")) sec.split_by = "largest_diamond_source";
    setSections((xs) => [...xs, sec]);
  }

  async function save(asNew = false) {
    if (!sections.length) { setMsg("Add at least one section."); return; }
    if (editing && !asNew) {
      await api.updateTemplate(editing.id, { name, description: desc, spec: { sections } });
    } else {
      await api.createTemplate(name, desc, { sections });
    }
    setMsg("Saved ✓");
    onSaved();
  }

  return (
    <div className="card p-4 space-y-3">
      {editing && (
        <div className="flex items-center justify-between bg-frost border border-cloud rounded-md px-3 py-2 text-sm">
          <span>Editing <strong>{editing.name}</strong>{editing.is_seed && " — saving keeps a copy so the original seed stays intact"}</span>
          <button className="text-xs text-slate hover:text-coral" onClick={onCancel}>Cancel</button>
        </div>
      )}
      <div>
        <div className="text-slate font-semibold text-sm mb-1">Report name</div>
        <input className="input w-full" value={name} onChange={(e) => setName(e.target.value)} />
      </div>
      <input className="input w-full text-sm" placeholder="Description (optional)" value={desc} onChange={(e) => setDesc(e.target.value)} />

      <div className="border-t border-cloud pt-3">
        <div className="text-slate font-semibold text-sm mb-1">Add a section</div>
        <select className="input w-full mb-2" value={kind} onChange={(e) => setKind(e.target.value)}>
          <option value="callout">Callout (single number)</option>
          <option value="metric_over_time">Metric over time</option>
          <option value="breakdown">Breakdown by attribute</option>
          <option value="split_share">Share over time</option>
        </select>
        {(kind === "callout" || kind === "metric_over_time") && (
          <select className="input w-full mb-2" value={metric} onChange={(e) => setMetric(e.target.value)}>
            {metrics.map((m: any) => <option key={m.key} value={m.key}>{m.label}</option>)}
          </select>
        )}
        {(kind === "breakdown" || kind === "split_share") && (
          <select className="input w-full mb-2" value={dimension} onChange={(e) => setDimension(e.target.value)}>
            {attrs.map((a: any) => <option key={a.key} value={a.key}>{a.label}</option>)}
          </select>
        )}
        {(kind === "metric_over_time" || kind === "breakdown") && (
          <label className="text-sm flex items-center gap-2 mb-2">
            <input type="checkbox" checked={split} onChange={(e) => setSplit(e.target.checked)} />
            Split by Natural vs Lab
          </label>
        )}
        <button className="btn-ghost w-full text-sm" onClick={addSection}>+ Add section</button>
      </div>

      {sections.length > 0 && (
        <div className="border-t border-cloud pt-3">
          <div className="text-slate font-semibold text-sm mb-1">Sections ({sections.length})</div>
          {sections.map((s, i) => (
            <div key={i} className="flex items-center justify-between text-sm py-1">
              <span>{s.title}</span>
              <button className="text-coral text-xs" onClick={() => setSections((xs) => xs.filter((_, j) => j !== i))}>remove</button>
            </div>
          ))}
        </div>
      )}

      {editing ? (
        <div className="flex gap-2">
          <button className="btn-primary flex-1" onClick={() => save(false)}>Save changes</button>
          <button className="btn-ghost flex-1" onClick={() => save(true)}>Save as new</button>
        </div>
      ) : (
        <button className="btn-primary w-full" onClick={() => save(false)}>Save as template</button>
      )}
      {msg && <div className="text-sm text-teal">{msg}</div>}
    </div>
  );
}
