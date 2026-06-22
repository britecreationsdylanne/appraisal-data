import { ReactNode, useState } from "react";
import { NavLink } from "react-router-dom";
import { useApp } from "../state";
import DateRangeControl from "./DateRangeControl";
import FactsTray from "./FactsTray";
import ExportModal from "./ExportModal";

// Primary modes, alphabetical.
const PRIMARY = [
  { to: "/chat", label: "Chat", hint: "Ask the data" },
  { to: "/fact-finder", label: "Fact Finder", hint: "Turn a blog into data" },
  { to: "/reports", label: "Reports", hint: "Build & re-run" },
  { to: "/trends", label: "Trends", hint: "Spot real movement" },
];
// Set apart — it's a different kind of thing (output, not analysis).
const TOOLS = [{ to: "/export", label: "Export Studio", hint: "Branded images" }];

function navClass(isActive: boolean, accent: "mint" | "orange") {
  const active = accent === "orange" ? "border-orange bg-orange/20" : "border-mint bg-teal/30";
  return `block px-6 py-3.5 transition border-l-4 ${isActive ? active : "border-transparent hover:bg-white/5"}`;
}

export default function Shell({ children }: { children: ReactNode }) {
  const { meta, user, setUser } = useApp();
  const [navOpen, setNavOpen] = useState(false);

  const changeUser = () => {
    const name = window.prompt("Who are you? (used to keep your saved questions private)", user);
    if (name != null) setUser(name);
  };

  return (
    <div className="min-h-screen bg-frost text-navy">
      {/* Mobile overlay */}
      {navOpen && <div className="fixed inset-0 bg-navy/40 z-30 lg:hidden" onClick={() => setNavOpen(false)} />}

      {/* Sidebar (off-canvas on mobile) */}
      <aside
        className={`fixed inset-y-0 left-0 w-72 bg-navy text-white flex flex-col z-40 transform transition-transform
          lg:translate-x-0 ${navOpen ? "translate-x-0" : "-translate-x-full"}`}
      >
        <div className="px-6 py-6 border-b border-white/10 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="inline-flex items-center justify-center w-10 h-10 rounded-full bg-mint shrink-0">
              <svg width="22" height="22" viewBox="0 0 16 16">
                <path d="M3 8 l3 3 l7 -8" stroke="#272D3F" strokeWidth="2.5" fill="none" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </span>
            <div className="leading-tight">
              <div className="font-semibold text-lg">Appraisal</div>
              <div className="text-sm text-mist">Data Research</div>
            </div>
          </div>
          <button className="lg:hidden text-mist text-2xl leading-none" onClick={() => setNavOpen(false)}>×</button>
        </div>
        <div className="flex-1 py-3 overflow-auto">
          <div className="mt-1 mb-1 px-6 text-[11px] uppercase tracking-wider text-mist/70">Data Requests</div>
          {PRIMARY.map((n) => (
            <NavLink key={n.to} to={n.to} onClick={() => setNavOpen(false)}
              className={({ isActive }) => navClass(isActive, "mint")}>
              <div className="font-semibold text-[17px]">{n.label}</div>
              <div className="text-sm text-mist">{n.hint}</div>
            </NavLink>
          ))}

          <div className="mt-4 mb-1 px-6 text-[11px] uppercase tracking-wider text-mist/70">Image Requests</div>
          {TOOLS.map((n) => (
            <NavLink key={n.to} to={n.to} onClick={() => setNavOpen(false)}
              className={({ isActive }) => navClass(isActive, "orange")}>
              <div className="font-semibold text-[17px]">{n.label}</div>
              <div className="text-sm text-mist">{n.hint}</div>
            </NavLink>
          ))}
        </div>
        <div className="px-6 py-4 text-xs text-mist border-t border-white/10">
          {meta ? (
            <>
              <div>{meta.row_count.toLocaleString()} appraisals</div>
              <div className="mt-1">
                Souls:{" "}
                <span className={meta.souls_live ? "text-mint" : "text-mist"}>
                  {meta.souls_live ? "live (Claude)" : "fallback (offline)"}
                </span>
              </div>
            </>
          ) : (
            "Loading…"
          )}
        </div>
      </aside>

      {/* Content column */}
      <div className="lg:pl-72 flex flex-col min-h-screen">
        <header className="sticky top-0 z-20 bg-white border-b border-cloud px-4 sm:px-6 py-3 flex items-center justify-between gap-3 flex-wrap">
          <div className="flex items-center gap-3 min-w-0">
            <button className="lg:hidden text-navy text-2xl leading-none px-1" onClick={() => setNavOpen(true)} aria-label="Menu">☰</button>
            <DateRangeControl />
          </div>
          <div className="flex items-center gap-3 whitespace-nowrap">
            {meta && (
              <span className="hidden sm:inline text-xs text-slate">
                {meta.date_bounds.min} → {meta.date_bounds.max}
              </span>
            )}
            <button
              className="text-sm font-semibold text-teal border border-cloud rounded-full px-3 py-1 hover:bg-frost"
              onClick={changeUser}
              title="Switch user"
            >
              You: {user}
            </button>
          </div>
        </header>

        <main className="flex-1 overflow-auto">
          <div className="max-w-[1700px] flex flex-col 2xl:flex-row items-start gap-6 2xl:gap-8 px-4 sm:px-6 lg:px-10 py-6 lg:py-8">
            <div className="flex-1 min-w-0 w-full">{children}</div>
            <FactsTray />
          </div>
        </main>
      </div>

      <ExportModal />
    </div>
  );
}
