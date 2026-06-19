import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { SERIES } from "../brand";

interface Props {
  kind: "line" | "bar" | "pie";
  x: (string | number)[];
  series: Record<string, (number | null)[]>;
  height?: number;
  stacked?: boolean;
}

export default function Chart({ kind, x, series, height = 260, stacked = false }: Props) {
  const names = Object.keys(series);

  if (kind === "pie") {
    const values = series[names[0]] || [];
    let slices = x.map((label, i) => ({ name: String(label), value: Number(values[i] ?? 0) }));
    slices.sort((a, b) => b.value - a.value);
    if (slices.length > 9) {
      const head = slices.slice(0, 9);
      const others = slices.slice(9).reduce((s, d) => s + d.value, 0);
      slices = [...head, { name: "Others", value: others }];
    }
    return (
      <ResponsiveContainer width="100%" height={height + 20}>
        <PieChart>
          <Pie data={slices} dataKey="value" nameKey="name" cx="42%" cy="50%" outerRadius={height * 0.42} innerRadius={height * 0.22}
               label={(e: any) => `${(e.percent * 100).toFixed(0)}%`} labelLine={false}>
            {slices.map((_, i) => <Cell key={i} fill={SERIES[i % SERIES.length]} />)}
          </Pie>
          <Tooltip formatter={(v: any) => Number(v).toLocaleString()} contentStyle={{ borderRadius: 8, border: "1px solid #E1E7EF", fontSize: 13 }} />
          <Legend layout="vertical" align="right" verticalAlign="middle" wrapperStyle={{ fontSize: 12 }} />
        </PieChart>
      </ResponsiveContainer>
    );
  }
  const data = x.map((xv, i) => {
    const row: any = { x: xv };
    names.forEach((n) => (row[n] = series[n][i] ?? null));
    return row;
  });

  const common = (
    <>
      <CartesianGrid strokeDasharray="3 3" stroke="#E1E7EF" vertical={false} />
      <XAxis dataKey="x" tick={{ fontSize: 12, fill: "#7DA3AF" }} />
      <YAxis tick={{ fontSize: 12, fill: "#7DA3AF" }} width={56} />
      <Tooltip contentStyle={{ borderRadius: 8, border: "1px solid #E1E7EF", fontSize: 13 }} />
      <Legend wrapperStyle={{ fontSize: 12 }} />
    </>
  );

  return (
    <ResponsiveContainer width="100%" height={height}>
      {kind === "line" ? (
        <LineChart data={data} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
          {common}
          {names.map((n, i) => (
            <Line key={n} type="monotone" dataKey={n} stroke={SERIES[i % SERIES.length]} strokeWidth={2.5} dot={false} />
          ))}
        </LineChart>
      ) : (
        <BarChart data={data} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
          {common}
          {names.map((n, i) => (
            <Bar key={n} dataKey={n} fill={SERIES[i % SERIES.length]} radius={[3, 3, 0, 0]} stackId={stacked ? "s" : undefined} />
          ))}
        </BarChart>
      )}
    </ResponsiveContainer>
  );
}
