import { useEffect, useState } from "react";
import { api } from "../api";
import { useApp } from "../state";

const VIEWS = [
  { key: "share", label: "Share of mix over time" },
  { key: "volume", label: "Volume over time" },
  { key: "value", label: "Average appraised value" },
];

export default function ExportStudio() {
  const { meta, range, user, openExport } = useApp();
  const [saved, setSaved] = useState<any[]>([]);
  const [dim, setDim] = useState("source");
  const [value, setValue] = useState("lab");
  const [view, setView] = useState("share");
  const [title, setTitle] = useState("");
  const [subtitle, setSubtitle] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  const loadSaved = () => api.savedItems("image").then(setSaved).catch(() => {});
  useEffect(() => { loadSaved(); }, [user]);

  const attrs = (meta?.attributes || []).filter((a: any) => !a.placeholder);
  const current = attrs.find((a: any) => a.key === dim);

  async function openEditor() {
    setBusy(true);
    setErr("");
    try {
      const tr = await api.trends(dim, value, range);
      const f = tr.findings.find((x: any) => x.kind === view) || tr.findings[0];
      if (!f || !f.chart) throw new Error("No chartable data for that selection");
      const c = f.chart;
      const series = c.series ? c.series : { [c.y_label || "value"]: c.y };
      openExport({
        title: title || f.title,
        subtitle: subtitle || `${range.start} → ${range.end}`,
        footer: `BriteCo appraisal data · n=${f.n.toLocaleString()} · ${f.label}`,
        kind: c.type === "bar" ? "bar" : "line",
        labels: c.x,
        series,
      });
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <h1 className="text-2xl font-semibold mb-1">Export Studio — branded visuals</h1>
      <p className="text-slate mb-4 max-w-3xl">
        Build an on-brand image, tweak it by chatting, and save it. The period and sample size are baked
        into the footer so a stat never travels without its caveat.
      </p>
      <div className="card p-3 mb-4 bg-frost border-mint/40 text-sm text-steel">
        💡 Fastest path: hit <strong>“Export image”</strong> on any <strong>Trends</strong> finding or
        <strong> Reports</strong> chart — it opens the editor pre-loaded with that exact data. Use the form
        below for a quick ad-hoc chart.
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Ad-hoc builder */}
        <div className="lg:col-span-5 card p-4 space-y-3 self-start">
          <div className="font-semibold text-navy">Quick chart</div>
          <div>
            <div className="text-slate font-semibold text-sm mb-1">Attribute</div>
            <select className="input w-full" value={dim} onChange={(e) => { setDim(e.target.value); const a = attrs.find((x: any) => x.key === e.target.value); setValue(a?.values?.[0] ?? ""); }}>
              {attrs.map((a: any) => <option key={a.key} value={a.key}>{a.label}</option>)}
            </select>
          </div>
          <div>
            <div className="text-slate font-semibold text-sm mb-1">Value</div>
            {current?.values?.length ? (
              <select className="input w-full" value={value} onChange={(e) => setValue(e.target.value)}>
                {current.values.map((v: string) => <option key={v} value={v}>{current.value_labels?.[v] ?? v}</option>)}
              </select>
            ) : <input className="input w-full" value={value} onChange={(e) => setValue(e.target.value)} />}
          </div>
          <div>
            <div className="text-slate font-semibold text-sm mb-1">View</div>
            <select className="input w-full" value={view} onChange={(e) => setView(e.target.value)}>
              {VIEWS.map((v) => <option key={v.key} value={v.key}>{v.label}</option>)}
            </select>
          </div>
          <input className="input w-full" placeholder="Title (auto if blank)" value={title} onChange={(e) => setTitle(e.target.value)} />
          <input className="input w-full" placeholder="Subtitle (auto if blank)" value={subtitle} onChange={(e) => setSubtitle(e.target.value)} />
          <button className="btn-primary w-full" onClick={openEditor} disabled={busy}>{busy ? "Loading…" : "Open in editor →"}</button>
          {err && <div className="text-coral text-sm">{err}</div>}
        </div>

        {/* Saved images gallery */}
        <div className="lg:col-span-7">
          <div className="flex items-center justify-between mb-2">
            <div className="font-semibold text-navy">My saved images ({saved.length})</div>
            <button className="text-xs text-teal font-semibold" onClick={loadSaved}>Refresh</button>
          </div>
          <div className="text-xs text-slate mb-3">Private to <strong>{user}</strong>. Open to re-edit, re-size, or download.</div>
          {!saved.length && <div className="card p-6 text-slate text-sm">No saved images yet. Build one and click “Save to my images”.</div>}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {saved.map((img) => (
              <div key={img.id} className="card p-3">
                <div className="bg-frost rounded p-2 flex justify-center h-36 overflow-hidden items-center">
                  <div style={{ width: 200 }} dangerouslySetInnerHTML={{ __html: img.payload?.svg || "" }} />
                </div>
                <div className="font-semibold text-sm mt-2 truncate">{img.title}</div>
                <div className="text-xs text-slate">{img.summary} · {img.created_at?.slice(0, 16)}</div>
                <div className="flex gap-3 mt-2 text-xs">
                  <button className="text-teal font-semibold" onClick={() => openExport(img.payload.spec)}>Open</button>
                  <button className="text-slate hover:text-coral" onClick={async () => { await api.deleteSaved(img.id); loadSaved(); }}>Delete</button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
