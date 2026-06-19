// BriteCo palette + chart series colors (briteco-branding skill)
export const C = {
  navy: "#272D3F",
  slate: "#7DA3AF",
  teal: "#008182",
  mint: "#31D7CA",
  cloud: "#E1E7EF",
  frost: "#F4F7FC",
  orange: "#FC883A",
  coral: "#D73D4F",
};

export const SERIES = ["#008182", "#FC883A", "#9b87f5", "#4285F4", "#31D7CA", "#7DA3AF", "#466F88"];

export const CONFIDENCE: Record<string, { dot: string; bg: string; text: string; label: string }> = {
  Strong: { dot: "#1E9E6A", bg: "#E6F5EE", text: "#137A50", label: "Strong" },
  Directional: { dot: "#FC883A", bg: "#FFE5D9", text: "#B85A18", label: "Directional" },
  "Part of a broader trend": { dot: "#7DA3AF", bg: "#E1E7EF", text: "#466F88", label: "Broader trend" },
  "Not significant": { dot: "#A9C1CB", bg: "#F4F7FC", text: "#7DA3AF", label: "Not significant" },
};

export function fmtCurrency(v: number | null) {
  if (v == null) return "—";
  return "$" + Math.round(v).toLocaleString();
}
export function fmtInt(v: number | null) {
  if (v == null) return "—";
  return Math.round(v).toLocaleString();
}
