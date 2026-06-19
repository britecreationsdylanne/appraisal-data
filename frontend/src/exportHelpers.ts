import { ExportSpec } from "./state";

export function specFromFinding(f: any, period: string): ExportSpec | null {
  if (!f.chart) return null;
  const c = f.chart;
  const series = c.series ? c.series : { [c.y_label || "value"]: c.y };
  return {
    title: f.title,
    subtitle: period,
    footer: `BriteCo appraisal data · n=${(f.n || 0).toLocaleString()} · ${f.label}`,
    kind: c.type === "bar" ? "bar" : "line",
    labels: c.x,
    series,
  };
}

export function specFromSection(s: any, period: string): ExportSpec | null {
  const d = s.data;
  if (!d) return null;
  const footer = `BriteCo appraisal data · ${period}${s.n != null ? ` · n=${s.n.toLocaleString()}` : ""}`;

  if (s.kind === "metric_over_time") {
    return { title: s.title, subtitle: period, footer, kind: "line", labels: d.periods, series: d.series };
  }
  if (s.kind === "split_share") {
    const series: Record<string, number[]> = {};
    d.keys.forEach((k: string) => (series[k] = d.shares[k].map((v: number) => +(v * 100).toFixed(1))));
    return { title: s.title, subtitle: period, footer, kind: "line", labels: d.periods, series };
  }
  if (s.kind === "breakdown_2d") {
    return { title: s.title, subtitle: period, footer, kind: "bar", labels: d.a_keys, series: d.series };
  }
  if (s.kind === "breakdown") {
    if (d.groups) {
      const keys = Array.from(new Set(Object.values(d.groups).flatMap((g: any) => g.map((x: any) => x.key))));
      const series: Record<string, (number | null)[]> = {};
      Object.entries(d.groups).forEach(([split, rows]: any) => {
        series[split] = keys.map((k) => rows.find((r: any) => r.key === k)?.value ?? 0);
      });
      return { title: s.title, subtitle: period, footer, kind: "bar", labels: keys as string[], series };
    }
    const items = (d.items || []);
    // Distributions export as a donut (match the in-app view); averages as bars.
    const isDistribution = d.metric === "piece_count" || d.metric === "total_appraised_value";
    const top = items.slice(0, isDistribution ? 20 : 12);
    return {
      title: s.title, subtitle: period, footer, kind: isDistribution ? "pie" : "bar",
      labels: top.map((i: any) => i.key), series: { [d.label]: top.map((i: any) => i.value) },
    };
  }
  return null;
}
