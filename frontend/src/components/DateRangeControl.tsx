import { useApp } from "../state";

// Presets are computed against the data's max date (its "today").
function presets(min: string, max: string) {
  const hi = new Date(max);
  const y = hi.getFullYear();
  const iso = (d: Date) => d.toISOString().slice(0, 10);
  const back = (months: number) => {
    const d = new Date(hi);
    d.setMonth(d.getMonth() - months);
    return iso(d);
  };
  return [
    { key: "all", label: "All time", start: min, end: max },
    { key: "ytd", label: "Year to date", start: `${y}-01-01`, end: max },
    { key: "last_year", label: "Last full year", start: `${y - 1}-01-01`, end: `${y - 1}-12-31` },
    { key: "12m", label: "Last 12 months", start: back(12), end: max },
    { key: "4q", label: "Last 4 quarters", start: back(12), end: max },
  ];
}

export default function DateRangeControl() {
  const { meta, range, setRange } = useApp();
  if (!meta) return null;
  const { min, max } = meta.date_bounds;
  const ps = presets(min, max);

  return (
    <div className="flex flex-wrap items-center gap-2 text-sm">
      <span className="text-slate font-semibold mr-1">Date range</span>
      <select
        className="input py-1.5"
        value=""
        onChange={(e) => {
          const p = ps.find((x) => x.key === e.target.value);
          if (p) setRange({ ...range, start: p.start, end: p.end });
        }}
      >
        <option value="">Presets…</option>
        {ps.map((p) => (
          <option key={p.key} value={p.key}>
            {p.label}
          </option>
        ))}
      </select>
      <input
        type="date"
        className="input py-1.5"
        min={min}
        max={max}
        value={range.start}
        onChange={(e) => setRange({ ...range, start: e.target.value })}
      />
      <span className="text-slate">→</span>
      <input
        type="date"
        className="input py-1.5"
        min={min}
        max={max}
        value={range.end}
        onChange={(e) => setRange({ ...range, end: e.target.value })}
      />
      <span className="text-slate font-semibold ml-2">by</span>
      <select
        className="input py-1.5"
        value={range.granularity}
        onChange={(e) => setRange({ ...range, granularity: e.target.value })}
      >
        {meta.granularities.map((g: string) => (
          <option key={g} value={g}>
            {g}
          </option>
        ))}
      </select>
    </div>
  );
}
