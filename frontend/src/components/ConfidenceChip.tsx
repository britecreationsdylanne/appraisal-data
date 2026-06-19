import { CONFIDENCE } from "../brand";

export default function ConfidenceChip({ label }: { label: string }) {
  const c = CONFIDENCE[label] || CONFIDENCE["Not significant"];
  return (
    <span
      className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-semibold"
      style={{ background: c.bg, color: c.text }}
    >
      <span className="inline-block w-2 h-2 rounded-full" style={{ background: c.dot }} />
      {c.label}
    </span>
  );
}

export function NBadge({ n }: { n: number }) {
  return (
    <span className="inline-block rounded-full bg-frost border border-cloud px-2 py-0.5 text-xs text-slate">
      n = {n.toLocaleString()}
    </span>
  );
}
