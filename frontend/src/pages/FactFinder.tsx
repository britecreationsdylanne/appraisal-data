import { useState } from "react";
import { api } from "../api";
import { useApp } from "../state";
import Chart from "../components/Chart";
import ConfidenceChip, { NBadge } from "../components/ConfidenceChip";

export default function FactFinder() {
  const { range, addFact } = useApp();
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [err, setErr] = useState("");

  async function find() {
    if (!text.trim()) return;
    setBusy(true);
    setErr("");
    try {
      setResult(await api.factFinder(text));
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="w-full">
      <h1 className="text-2xl font-semibold mb-1">Fact Finder — turn a draft into data</h1>
      <p className="text-slate mb-4 max-w-3xl">
        Paste your blog copy and Fact Finder reads it, then hands you real stats from the appraisal data
        you can drop straight into the piece — and flags any claim the numbers don't back up.
      </p>

      <div className="card p-4">
        <textarea
          className="input w-full text-sm"
          rows={7}
          placeholder="Paste your blog draft here…"
          value={text}
          onChange={(e) => setText(e.target.value)}
        />
        <div className="flex items-center justify-between mt-2">
          <span className="text-xs text-slate">{text.trim() ? `${text.trim().split(/\s+/).length} words` : "Paste a draft to begin"}</span>
          <button className="btn-primary" onClick={find} disabled={busy || !text.trim()}>
            {busy ? "Reading…" : "Find facts →"}
          </button>
        </div>
      </div>

      {err && <div className="mt-4 text-coral text-sm">{err}</div>}

      {result && (
        <div className="mt-6 space-y-5">
          <div className="card p-4 border-l-4 border-teal">
            <div className="text-xs uppercase tracking-wide text-slate font-semibold">
              What it read {result.souls_live ? "(Claude)" : "(offline keyword mode)"}
            </div>
            <div className="text-navy mt-1">{result.summary}</div>
            {!!result.topics?.length && (
              <div className="flex flex-wrap gap-2 mt-2">
                {result.topics.map((t: string, i: number) => (
                  <span key={i} className="text-xs bg-frost border border-cloud rounded-full px-2.5 py-0.5 text-steel">{t}</span>
                ))}
              </div>
            )}
          </div>

          {!!result.claim_checks?.length && (
            <div className="card p-4">
              <div className="font-semibold mb-2">Claim check</div>
              {result.claim_checks.map((c: any, i: number) => (
                <div key={i} className="flex items-start gap-2 text-sm py-1">
                  <span>{c.checkable ? "✅" : "⚠️"}</span>
                  <div>
                    <span className="text-navy">{c.claim}</span>
                    {c.note && <span className="text-slate"> — {c.note}</span>}
                  </div>
                </div>
              ))}
            </div>
          )}

          <div>
            <div className="font-semibold text-navy mb-2">Suggested stats to pull ({result.suggestions.length})</div>
            <div className="space-y-3">
              {result.suggestions.map((s: any, i: number) => (
                <Suggestion key={i} s={s} range={range} onPin={addFact} />
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function Suggestion({ s, range, onPin }: { s: any; range: any; onPin: (f: any) => void }) {
  const [question, setQuestion] = useState(s.question);
  const [busy, setBusy] = useState(false);
  const [ans, setAns] = useState<any>(null);

  async function run() {
    setBusy(true);
    try {
      setAns(await api.chat(question, range));
    } finally {
      setBusy(false);
    }
  }

  const result = ans?.data?.result;
  const overTime = ans?.data?.kind === "over_time";
  let value: string | undefined;
  if (ans && !overTime && result) {
    value = result.value == null ? "—"
      : (result.label?.toLowerCase().includes("value") || result.label?.toLowerCase().includes("price"))
      ? "$" + Math.round(result.value).toLocaleString()
      : Number.isInteger(result.value) ? Math.round(result.value).toLocaleString() : result.value.toFixed(2);
  }

  return (
    <div className="card p-4">
      <div className="text-xs text-slate mb-1">{s.rationale}</div>
      <div className="flex flex-col sm:flex-row gap-2">
        <input className="input flex-1" value={question} onChange={(e) => setQuestion(e.target.value)} />
        <button className="btn-primary" onClick={run} disabled={busy}>{busy ? "…" : "Run"}</button>
      </div>

      {ans && (
        <div className="mt-3 border-t border-cloud pt-3">
          <div className="text-navy">{ans.answer}</div>
          <div className="flex items-center gap-2 mt-2 flex-wrap">
            <ConfidenceChip label={ans.confidence} />
            <NBadge n={ans.n} />
          </div>
          <div className="text-sm text-steel mt-1">⚠ {ans.caveat}</div>
          {overTime && result && (
            <div className="mt-3"><Chart kind={result.split_by ? "bar" : "line"} x={result.periods} series={result.series} /></div>
          )}
          <div className="mt-2 text-right">
            <button className="btn-ghost text-sm" onClick={() => onPin({ ...ans.fact, value, source: "fact-finder" })}>
              Pin to facts
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
