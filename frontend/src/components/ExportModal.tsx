import { useEffect, useState } from "react";
import { api } from "../api";
import { useApp, ExportSpec } from "../state";

export default function ExportModal() {
  const { exportSpec, closeExport } = useApp();
  const [sizes, setSizes] = useState<any[]>([]);
  const [size, setSize] = useState("ig_square");
  const [spec, setSpec] = useState<ExportSpec | null>(null);
  const [render, setRender] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  const [tweak, setTweak] = useState("");
  const [soulsLive, setSoulsLive] = useState(false);
  const [savedMsg, setSavedMsg] = useState("");

  useEffect(() => {
    if (exportSpec && !sizes.length) api.exportSizes().then(setSizes);
  }, [exportSpec]);

  useEffect(() => {
    if (exportSpec) {
      setSpec(exportSpec);
      setTweak("");
      build(exportSpec, size);
    } else {
      setRender(null);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [exportSpec]);

  async function build(sp: ExportSpec, sz: string) {
    setBusy(true);
    try {
      setRender(await api.exportSvg(sp, sz));
    } finally {
      setBusy(false);
    }
  }

  async function applyTweak() {
    if (!spec || !tweak.trim()) return;
    setBusy(true);
    try {
      const res = await api.exportEdit(spec, tweak, size);
      setSpec(res.spec);
      setSoulsLive(res.souls_live);
      setRender(res);
      setTweak("");
    } finally {
      setBusy(false);
    }
  }

  async function saveToHistory() {
    if (!spec || !render) return;
    await api.createSaved({
      kind: "image",
      title: spec.title || "Image",
      summary: render.size_label,
      payload: { spec, size, svg: render.svg, width: render.width, height: render.height },
    });
    setSavedMsg("Saved to your images ✓");
    setTimeout(() => setSavedMsg(""), 2500);
  }

  function download(kind: "svg" | "png") {
    if (!render) return;
    const blob = new Blob([render.svg], { type: "image/svg+xml" });
    const url = URL.createObjectURL(blob);
    if (kind === "svg") {
      const a = document.createElement("a");
      a.href = url;
      a.download = `appraisal-${size}.svg`;
      a.click();
      return;
    }
    const img = new Image();
    img.onload = () => {
      const c = document.createElement("canvas");
      c.width = render.width;
      c.height = render.height;
      c.getContext("2d")!.drawImage(img, 0, 0);
      c.toBlob((b) => {
        if (!b) return;
        const a = document.createElement("a");
        a.href = URL.createObjectURL(b);
        a.download = `appraisal-${size}.png`;
        a.click();
      });
    };
    img.src = url;
  }

  if (!exportSpec || !spec) return null;

  return (
    <div className="fixed inset-0 z-50 bg-navy/40 flex items-center justify-center p-6" onClick={closeExport}>
      <div className="bg-white rounded-lg shadow-xl w-full max-w-4xl max-h-[92vh] overflow-auto" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between px-5 py-3 border-b border-cloud">
          <div className="font-semibold text-navy">Export image</div>
          <button className="text-slate hover:text-coral" onClick={closeExport}>✕</button>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 p-5">
          {/* Preview */}
          <div className="lg:col-span-7">
            <div className="bg-frost rounded-lg p-4 flex justify-center min-h-[320px] items-center">
              {busy && <div className="text-slate text-sm">Rendering…</div>}
              {render && !busy && (
                <div style={{ width: 360, maxWidth: "100%" }} dangerouslySetInnerHTML={{ __html: render.svg }} />
              )}
            </div>
          </div>

          {/* Controls */}
          <div className="lg:col-span-5 space-y-4">
            <div>
              <div className="text-sm text-slate font-semibold mb-1">Size</div>
              <select className="input w-full" value={size} onChange={(e) => { setSize(e.target.value); build(spec, e.target.value); }}>
                {sizes.map((s) => (
                  <option key={s.key} value={s.key}>{s.label} ({s.width}×{s.height})</option>
                ))}
              </select>
            </div>

            <div>
              <div className="text-sm text-slate font-semibold mb-1">Tweak it (chat)</div>
              <textarea
                className="input w-full text-sm"
                rows={2}
                placeholder='e.g. "make the background teal" or "turn it into a bar chart"'
                value={tweak}
                onChange={(e) => setTweak(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); applyTweak(); } }}
              />
              <button className="btn-primary w-full mt-2 text-sm" onClick={applyTweak} disabled={busy || !tweak.trim()}>
                Apply tweak
              </button>
              <p className="text-xs text-slate mt-1">
                {soulsLive
                  ? "Edited by Claude."
                  : "Offline mode handles: background color, accent color, bar/line. Add an API key for free-form edits."}
              </p>
            </div>

            <div className="pt-2 border-t border-cloud space-y-2">
              <button className="btn-primary text-sm w-full" onClick={saveToHistory} disabled={!render}>
                Save to my images
              </button>
              {savedMsg && <div className="text-xs text-teal text-center">{savedMsg}</div>}
              <div className="flex gap-2">
                <button className="btn-ghost text-sm flex-1" onClick={() => download("png")} disabled={!render}>Download PNG</button>
                <button className="btn-ghost text-sm flex-1" onClick={() => download("svg")} disabled={!render}>Download SVG</button>
              </div>
            </div>
            <p className="text-xs text-slate">
              The date range and sample size are baked into the footer, so the stat never travels without its caveat.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
