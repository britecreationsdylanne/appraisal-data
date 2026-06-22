import { useApp } from "../state";
import ConfidenceChip from "./ConfidenceChip";

export default function FactsTray() {
  const { facts, removeFact, clearFacts, openExport } = useApp();

  const copyAll = () => {
    const text = facts
      .map((f) => `• ${f.metric} — ${f.label}: ${f.value ?? ""} (${f.period}; n=${f.n}; ${f.confidence})`)
      .join("\n");
    navigator.clipboard?.writeText(text);
  };

  const makeImage = () => {
    if (!facts.length) return;
    openExport({
      title: "Key Facts",
      subtitle: facts[0]?.period ?? "",
      footer: "BriteCo · Appraisal Data Research",
      kind: "stats",
      stats: facts.slice(0, 6).map((f) => ({
        value: f.value && f.value.length <= 16 ? f.value : `n=${f.n.toLocaleString()}`,
        label: f.metric.length > 40 ? f.metric.slice(0, 40) + "…" : f.metric,
        sub: `${f.period} · n=${f.n.toLocaleString()} · ${f.confidence}`,
      })),
    });
  };

  return (
    <aside className="w-full 2xl:w-80 shrink-0 card flex flex-col 2xl:sticky 2xl:top-6 2xl:self-start 2xl:max-h-[calc(100vh-7rem)] overflow-hidden">
      <div className="px-4 py-3 border-b border-cloud flex items-center justify-between">
        <div className="font-semibold text-navy">Facts Tray</div>
        <div className="flex gap-2">
          <button className="text-xs text-teal font-semibold" onClick={makeImage} disabled={!facts.length}>
            Make image
          </button>
          <button className="text-xs text-teal font-semibold" onClick={copyAll} disabled={!facts.length}>
            Copy
          </button>
          <button className="text-xs text-slate" onClick={clearFacts} disabled={!facts.length}>
            Clear
          </button>
        </div>
      </div>
      <div className="flex-1 overflow-auto p-3 space-y-2">
        {!facts.length && (
          <p className="text-sm text-slate p-2">
            Pin facts here from Chat, Trends, or Reports. Each keeps its sample size and confidence so a
            stat never travels without its caveat.
          </p>
        )}
        {facts.map((f) => (
          <div key={f.id} className="card p-3 text-sm">
            <div className="flex items-start justify-between gap-2">
              <div className="font-semibold text-navy">{f.value ?? f.metric}</div>
              <button className="text-slate hover:text-coral text-xs" onClick={() => removeFact(f.id)}>
                ✕
              </button>
            </div>
            <div className="text-slate text-xs mt-0.5">{f.metric} · {f.label}</div>
            <div className="text-slate text-xs mt-0.5">{f.period}</div>
            <div className="mt-2 flex items-center gap-2">
              <ConfidenceChip label={f.confidence} />
              <span className="text-xs text-slate">n={f.n.toLocaleString()}</span>
            </div>
          </div>
        ))}
      </div>
      <div className="px-4 py-2 border-t border-cloud text-xs text-slate">{facts.length} pinned</div>
    </aside>
  );
}
