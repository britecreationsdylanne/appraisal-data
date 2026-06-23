import { useState } from "react";
import { ComposableMap, Geographies, Geography } from "react-simple-maps";
import { C } from "../brand";

// us-atlas TopoJSON (state shapes), bundled in /public so it works offline/in-cloud.
// geo.properties.name = full state name.
const GEO_URL = "/states-10m.json";

const NAME_TO_CODE: Record<string, string> = {
  Alabama: "AL", Alaska: "AK", Arizona: "AZ", Arkansas: "AR", California: "CA",
  Colorado: "CO", Connecticut: "CT", Delaware: "DE", Florida: "FL", Georgia: "GA",
  Hawaii: "HI", Idaho: "ID", Illinois: "IL", Indiana: "IN", Iowa: "IA",
  Kansas: "KS", Kentucky: "KY", Louisiana: "LA", Maine: "ME", Maryland: "MD",
  Massachusetts: "MA", Michigan: "MI", Minnesota: "MN", Mississippi: "MS", Missouri: "MO",
  Montana: "MT", Nebraska: "NE", Nevada: "NV", "New Hampshire": "NH", "New Jersey": "NJ",
  "New Mexico": "NM", "New York": "NY", "North Carolina": "NC", "North Dakota": "ND", Ohio: "OH",
  Oklahoma: "OK", Oregon: "OR", Pennsylvania: "PA", "Rhode Island": "RI", "South Carolina": "SC",
  "South Dakota": "SD", Tennessee: "TN", Texas: "TX", Utah: "UT", Vermont: "VT",
  Virginia: "VA", Washington: "WA", "West Virginia": "WV", Wisconsin: "WI", Wyoming: "WY",
  "District of Columbia": "DC",
};

function lerp(a: string, b: string, t: number) {
  const ah = a.match(/\w\w/g)!.map((h) => parseInt(h, 16));
  const bh = b.match(/\w\w/g)!.map((h) => parseInt(h, 16));
  const mix = ah.map((v, i) => Math.round(v + (bh[i] - v) * t));
  return `rgb(${mix[0]},${mix[1]},${mix[2]})`;
}

function fmt(v: number, mode: string) {
  if (mode === "share") return `${(v * 100).toFixed(1)}%`;
  if (v >= 1000) return `$${Math.round(v).toLocaleString()}`;
  return v.toFixed(2);
}

interface Props {
  byState: Record<string, number>;
  min: number;
  max: number;
  mode: string;
  label: string;
}

export default function USMap({ byState, min, max, mode, label }: Props) {
  const [hover, setHover] = useState<{ name: string; v: number | null } | null>(null);
  const span = max - min || 1;

  return (
    <div className="mt-3">
      <ComposableMap projection="geoAlbersUsa" width={780} height={420} style={{ width: "100%", height: "auto" }}>
        <Geographies geography={GEO_URL}>
          {({ geographies }: any) =>
            geographies.map((geo: any) => {
              const code = NAME_TO_CODE[geo.properties.name];
              const v = code != null ? byState[code] : undefined;
              const fill = v == null ? C.cloud : lerp("#E1E7EF", "#008182", (v - min) / span);
              return (
                <Geography
                  key={geo.rsmKey}
                  geography={geo}
                  fill={fill}
                  stroke="#FFFFFF"
                  strokeWidth={0.5}
                  style={{ default: { outline: "none" }, hover: { outline: "none", fill: C.orange }, pressed: { outline: "none" } }}
                  onMouseEnter={() => setHover({ name: geo.properties.name, v: v ?? null })}
                  onMouseLeave={() => setHover(null)}
                />
              );
            })
          }
        </Geographies>
      </ComposableMap>
      <div className="flex items-center justify-between text-xs text-slate mt-1">
        <div className="flex items-center gap-2">
          <span>{fmt(min, mode)}</span>
          <span className="inline-block w-24 h-2 rounded" style={{ background: `linear-gradient(90deg, #E1E7EF, ${C.teal})` }} />
          <span>{fmt(max, mode)}</span>
          <span className="ml-2">{label}</span>
        </div>
        <div className="font-semibold text-navy">
          {hover ? `${hover.name}: ${hover.v == null ? "no data" : fmt(hover.v, mode)}` : "Hover a state"}
        </div>
      </div>
    </div>
  );
}
