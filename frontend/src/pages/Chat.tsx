import { useEffect, useState } from "react";
import { api } from "../api";
import { useApp } from "../state";
import Chart from "../components/Chart";
import ConfidenceChip, { NBadge } from "../components/ConfidenceChip";

const SUGGESTIONS = [
  "What's the average appraised value of lab grown oval engagement rings?",
  "How many natural diamond pieces by year?",
  "Average carat for lab grown diamonds over time",
  "Average appraised value, natural vs lab, by year",
];

export default function Chat() {
  const { range, addFact, user } = useApp();
  const [q, setQ] = useState("");
  const [busy, setBusy] = useState(false);
  const [items, setItems] = useState<any[]>([]);
  const [err, setErr] = useState("");
  const [history, setHistory] = useState<any[]>([]);
  const [library, setLibrary] = useState<any[]>([]);
  const [tab, setTab] = useState<"mine" | "library">("mine");

  const loadSaved = () => {
    api.chatHistory().then(setHistory).catch(() => {});
    api.chatLibrary().then(setLibrary).catch(() => {});
  };
  useEffect(() => { loadSaved(); }, [user]); // reload when the active user changes

  async function ask(question: string) {
    if (!question.trim()) return;
    setBusy(true);
    setErr("");
    try {
      const res = await api.chat(question, range);
      setItems((xs) => [res, ...xs]);
      setQ("");
      loadSaved();
    } catch (e: any) {
      setErr(e.message || "Something went wrong");
    } finally {
      setBusy(false);
    }
  }

  async function clearHistory() {
    await api.clearChatHistory();
    loadSaved();
  }

  async function toggleShare(id: number, shared: boolean) {
    await api.shareChat(id, shared);
    loadSaved();
  }

  async function deleteOne(id: number) {
    await api.deleteChat(id);
    loadSaved();
  }

  return (
    <div className="w-full">
      <h1 className="text-2xl font-semibold mb-1">Chat — ask the data</h1>
      <p className="text-slate mb-4 max-w-3xl">
        Natural-language questions become governed, read-only queries. Every answer carries its sample
        size and a caveat, scoped to your date range.
      </p>

      <div className="card p-4">
        <div className="flex gap-2">
          <input
            className="input flex-1"
            placeholder="Ask about appraised value, carat, counts, lab vs natural…"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && ask(q)}
          />
          <button className="btn-primary" onClick={() => ask(q)} disabled={busy}>
            {busy ? "Asking…" : "Ask →"}
          </button>
        </div>
        <div className="flex flex-wrap gap-2 mt-3">
          {SUGGESTIONS.map((s) => (
            <button key={s} className="text-xs text-teal border border-cloud rounded-full px-3 py-1 hover:bg-frost" onClick={() => ask(s)}>
              {s}
            </button>
          ))}
        </div>
      </div>

      {err && <div className="mt-4 text-coral text-sm">{err}</div>}

      {/* This session's answers */}
      <div className="mt-6 space-y-4">
        {items.map((it, i) => (
          <Answer key={i} it={it} onPin={addFact} />
        ))}
      </div>

      {/* Saved questions: private history + shared library */}
      <div className="mt-8">
        <div className="flex items-center justify-between mb-3">
          <div className="flex gap-2">
            <button
              className={`px-3 py-1.5 rounded-md text-sm font-semibold ${tab === "mine" ? "bg-teal text-white" : "btn-ghost"}`}
              onClick={() => setTab("mine")}
            >
              My questions ({history.length})
            </button>
            <button
              className={`px-3 py-1.5 rounded-md text-sm font-semibold ${tab === "library" ? "bg-teal text-white" : "btn-ghost"}`}
              onClick={() => setTab("library")}
            >
              Shared library ({library.length})
            </button>
          </div>
          {tab === "mine" && !!history.length && (
            <button className="text-xs text-slate hover:text-coral" onClick={clearHistory}>Clear my unshared</button>
          )}
        </div>

        {tab === "mine" && (
          <div className="space-y-2">
            <div className="text-xs text-slate mb-1">Private to <strong>{user}</strong>. Share one to put it in the team library.</div>
            {!history.length && <div className="text-sm text-slate">Your questions are saved here automatically.</div>}
            {history.map((h) => (
              <SavedRow key={h.id} h={h} user={user} onAsk={ask} onShare={toggleShare} onDelete={deleteOne} />
            ))}
          </div>
        )}

        {tab === "library" && (
          <div className="space-y-2">
            <div className="text-xs text-slate mb-1">Questions the team has shared. Anyone can re-run them.</div>
            {!library.length && <div className="text-sm text-slate">Nothing shared yet. Share a question from “My questions”.</div>}
            {library.map((h) => (
              <SavedRow key={h.id} h={h} user={user} onAsk={ask} onShare={toggleShare} onDelete={deleteOne} showOwner />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function SavedRow({ h, user, onAsk, onShare, onDelete, showOwner }: {
  h: any; user: string; onAsk: (q: string) => void;
  onShare: (id: number, shared: boolean) => void; onDelete: (id: number) => void; showOwner?: boolean;
}) {
  const mine = h.owner === user;
  return (
    <div className="card p-3 flex items-start justify-between gap-3">
      <div className="min-w-0">
        <div className="font-semibold text-navy text-sm">{h.question}</div>
        <div className="text-sm text-steel mt-0.5 truncate">{h.answer}</div>
        <div className="flex items-center gap-2 mt-1 flex-wrap">
          <ConfidenceChip label={h.confidence} />
          <span className="text-xs text-slate">n={h.n?.toLocaleString?.() ?? h.n}</span>
          <span className="text-xs text-slate">{h.created_at?.slice(0, 16)}</span>
          {showOwner && <span className="text-xs text-teal font-semibold">@{h.owner}</span>}
          {h.shared && !showOwner && <span className="text-xs text-teal font-semibold">shared</span>}
        </div>
      </div>
      <div className="flex flex-col gap-1 shrink-0">
        <button className="btn-ghost text-xs" onClick={() => onAsk(h.question)}>Ask again</button>
        {mine && (
          <button
            className={`text-xs font-semibold ${h.shared ? "text-slate" : "text-teal"}`}
            onClick={() => onShare(h.id, !h.shared)}
          >
            {h.shared ? "Unshare" : "Share"}
          </button>
        )}
        {mine && (
          <button className="text-xs text-slate hover:text-coral" onClick={() => onDelete(h.id)}>Delete</button>
        )}
      </div>
    </div>
  );
}

function Answer({ it, onPin }: { it: any; onPin: (f: any) => void }) {
  const result = it.data?.result;
  const overTime = it.data?.kind === "over_time";
  let value: string | undefined;
  if (!overTime && result) {
    value = result.value == null ? "—" : result.label?.toLowerCase().includes("value") || result.label?.toLowerCase().includes("price")
      ? "$" + Math.round(result.value).toLocaleString()
      : Number.isInteger(result.value) ? Math.round(result.value).toLocaleString() : result.value.toFixed(2);
  }

  return (
    <div className="card p-4">
      <div className="text-sm text-slate">{it.question}</div>
      <div className="text-lg text-navy mt-1">{it.answer}</div>
      <div className="flex items-center gap-2 mt-2">
        <ConfidenceChip label={it.confidence} />
        <NBadge n={it.n} />
        {!it.souls_live && <span className="text-xs text-slate">souls: offline fallback</span>}
      </div>
      <div className="text-sm text-steel mt-2">⚠ {it.caveat}</div>

      {overTime && result && (
        <div className="mt-4">
          <Chart kind={result.split_by ? "bar" : "line"} x={result.periods} series={result.series} />
        </div>
      )}

      <div className="mt-3 flex items-center justify-between">
        <details className="text-xs text-slate">
          <summary className="cursor-pointer">Show query plan</summary>
          <pre className="mt-2 bg-frost p-2 rounded overflow-auto">{JSON.stringify(it.plan, null, 2)}</pre>
        </details>
        <button
          className="btn-ghost text-sm"
          onClick={() => onPin({ ...it.fact, value, source: "chat" })}
        >
          Pin to facts
        </button>
      </div>
    </div>
  );
}
