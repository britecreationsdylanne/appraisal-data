import { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import { useApp } from "../state";
import { specFromFinding } from "../exportHelpers";
import Chart from "../components/Chart";
import ConfidenceChip, { NBadge } from "../components/ConfidenceChip";

export default function Trends() {
  const { meta, range, addFact, user } = useApp();
  const [dim, setDim] = useState("source");
  const [value, setValue] = useState("lab");
  const [busy, setBusy] = useState(false);
  const [res, setRes] = useState<any>(null);
  const [err, setErr] = useState("");
  const [history, setHistory] = useState<any[]>([]);

  const attrs = meta?.attributes || [];
  const grouped = useMemo(() => {
    const g: Record<string, any[]> = {};
    attrs.forEach((a: any) => (g[a.group] = [...(g[a.group] || []), a]));
    return g;
  }, [attrs]);
  const current = attrs.find((a: any) => a.key === dim);

  const loadHistory = () => api.savedItems("trend").then(setHistory).catch(() => {});
  useEffect(() => { loadHistory(); }, [user]);

  async function execute(d: string, v: string) {
    setBusy(true);
    setErr("");
    try {
      setRes(await api.trends(d, v, range));
      loadHistory();
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  }
  const run = () => execute(dim, value);
  const runAgain = (item: any) => {
    setDim(item.payload.dimension);
    setValue(item.payload.value);
    execute(item.payload.dimension, item.payload.value);
  };
  const removeHistory = async (id: number) => { await api.deleteSaved(id); loadHistory(); };

  return (
    <div className="w-full">
      <h1 className="text-2xl font-semibold mb-1">Trends — spot real movement</h1>
      <p className="text-slate mb-4 max-w-3xl">
        Pick an attribute and let the souls run the standard battery: share of mix, volume, and value over
        time — each measured against its baseline and labeled for significance so you never over-claim.
      </p>

      <div className="card p-4 flex flex-wrap items-end gap-3">
        <label className="text-sm">
          <div className="text-slate font-semibold mb-1">Attribute</div>
          <select
            className="input"
            value={dim}
            onChange={(e) => {
              const k = e.target.value;
              setDim(k);
              const a = attrs.find((x: any) => x.key === k);
              setValue(a?.values?.[0] ?? "");
            }}
          >
            {Object.entries(grouped).map(([group, list]) => (
              <optgroup key={group} label={group}>
                {(list as any[]).map((a) => (
                  <option key={a.key} value={a.key}>
                    {a.label}
                  </option>
                ))}
              </optgroup>
            ))}
          </select>
        </label>

        <label className="text-sm">
          <div className="text-slate font-semibold mb-1">Value</div>
          {current?.values?.length ? (
            <select className="input" value={value} onChange={(e) => setValue(e.target.value)}>
              {current.values.map((v: string) => (
                <option key={v} value={v}>
                  {current.value_labels?.[v] ?? v}
                </option>
              ))}
            </select>
          ) : (
            <input className="input" value={value} onChange={(e) => setValue(e.target.value)} placeholder="e.g. CA" />
          )}
        </label>

        <button className="btn-primary" onClick={run} disabled={busy}>
          {busy ? "Analyzing…" : current?.placeholder ? "Preview →" : "Run trend →"}
        </button>
      </div>

      {current?.placeholder && (
        <div className="mt-4 card p-4 bg-frost border-mint/40 text-sm text-steel">
          ⏳ <strong>{current.label}</strong> is a placeholder — the watch dataset
          ({current.needs_dataset}) isn't connected yet. Once it's wired in, this attribute runs the same
          battery (share, volume, value over time) as diamonds. Hit Preview to see the message.
        </div>
      )}

      {err && <div className="mt-4 text-coral text-sm">{err}</div>}

      {res && (
        <div className="mt-6">
          <div className="card p-4 border-l-4 border-teal">
            <div className="text-xs uppercase tracking-wide text-slate font-semibold">Souls' read</div>
            <div className="text-navy mt-1">{res.summary}</div>
          </div>

          <div className="mt-4 space-y-4">
            {res.findings.map((f: any, i: number) => (
              <Finding key={i} f={f} dimLabel={res.dimension_label} value={res.value}
                       period={`${res.date_start} → ${res.date_end}`} onPin={addFact} />
            ))}
          </div>
        </div>
      )}

      {/* My trend history */}
      <div className="mt-8">
        <div className="font-semibold text-navy mb-1">My trend runs ({history.length})</div>
        <div className="text-xs text-slate mb-2">Saved automatically, private to <strong>{user}</strong>.</div>
        <div className="space-y-2">
          {!history.length && <div className="text-sm text-slate">Run a trend and it's saved here.</div>}
          {history.map((h) => (
            <div key={h.id} className="card p-3 flex items-start justify-between gap-3">
              <div className="min-w-0">
                <div className="font-semibold text-navy text-sm">{h.title}</div>
                <div className="text-sm text-steel mt-0.5 truncate">{h.summary}</div>
                <div className="text-xs text-slate mt-0.5">{h.created_at?.slice(0, 16)}</div>
              </div>
              <div className="flex flex-col gap-1 shrink-0">
                <button className="btn-ghost text-xs" onClick={() => runAgain(h)}>Run again</button>
                <button className="text-xs text-slate hover:text-coral" onClick={() => removeHistory(h.id)}>Delete</button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function Finding({ f, dimLabel, value, period, onPin }: any) {
  const { openExport } = useApp();
  let series: Record<string, (number | null)[]> = {};
  let x: any[] = [];
  if (f.chart) {
    x = f.chart.x;
    series = f.chart.series ? f.chart.series : { [f.chart.y_label || "value"]: f.chart.y };
  }
  return (
    <div className="card p-4">
      <div className="flex items-start justify-between gap-3">
        <div className="font-semibold text-navy">{f.title}</div>
        <ConfidenceChip label={f.label} />
      </div>
      <div className="text-sm text-steel mt-1">{f.detail}</div>
      <div className="flex items-center gap-2 mt-2">
        <NBadge n={f.n} />
        {f.p_value != null && <span className="text-xs text-slate">p = {f.p_value}</span>}
      </div>
      {f.caveats?.map((c: string, i: number) => (
        <div key={i} className="text-sm text-coral mt-1">⚠ {c}</div>
      ))}
      {f.chart && (
        <div className="mt-3">
          <Chart kind={f.chart.type === "bar" ? "bar" : "line"} x={x} series={series} />
        </div>
      )}
      <div className="mt-3 flex justify-end gap-2">
        {f.chart && (
          <button
            className="btn-ghost text-sm"
            onClick={() => {
              const spec = specFromFinding(f, period);
              if (spec) openExport(spec);
            }}
          >
            Export image
          </button>
        )}
        <button
          className="btn-ghost text-sm"
          onClick={() =>
            onPin({
              metric: f.title, label: `${dimLabel} = ${value}`, value: f.detail,
              n: f.n, period, confidence: f.label, source: "trends",
            })
          }
        >
          Pin to facts
        </button>
      </div>
    </div>
  );
}
