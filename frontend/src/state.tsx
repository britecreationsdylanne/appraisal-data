import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { api, currentUser, setCurrentUser, DateRange } from "./api";

export interface Fact {
  id: string;
  metric: string;
  label: string;
  value?: string;
  n: number;
  period: string;
  confidence: string;
  source: string;
}

export interface ExportSpec {
  title: string;
  subtitle?: string;
  footer?: string;
  kind: "line" | "bar" | "stats" | "pie";
  labels?: (string | number)[];
  series?: Record<string, (number | null)[]>;
  stats?: { label: string; value: string; sub?: string }[];
  background?: string;
  accent?: string;
}

interface AppCtx {
  meta: any;
  ready: boolean;
  range: DateRange;
  setRange: (r: DateRange) => void;
  facts: Fact[];
  addFact: (f: Omit<Fact, "id">) => void;
  removeFact: (id: string) => void;
  clearFacts: () => void;
  exportSpec: ExportSpec | null;
  openExport: (s: ExportSpec) => void;
  closeExport: () => void;
  user: string;
  setUser: (name: string) => void;
}

const Ctx = createContext<AppCtx>(null as any);
export const useApp = () => useContext(Ctx);

export function AppProvider({ children }: { children: ReactNode }) {
  const [meta, setMeta] = useState<any>(null);
  const [range, setRange] = useState<DateRange>({ start: "2019-01-01", end: "2025-06-28", granularity: "year" });
  const [facts, setFacts] = useState<Fact[]>([]);
  const [exportSpec, setExportSpec] = useState<ExportSpec | null>(null);
  const [user, setUserState] = useState<string>(currentUser());
  const setUser = (name: string) => {
    setCurrentUser(name);
    setUserState(name.trim() || "local");
  };

  useEffect(() => {
    api.meta().then((m) => {
      setMeta(m);
      setRange((r) => ({ ...r, start: m.date_bounds.min, end: m.date_bounds.max }));
    });
  }, []);

  const addFact = (f: Omit<Fact, "id">) =>
    setFacts((xs) => [{ ...f, id: Math.random().toString(36).slice(2) }, ...xs]);
  const removeFact = (id: string) => setFacts((xs) => xs.filter((x) => x.id !== id));
  const clearFacts = () => setFacts([]);

  return (
    <Ctx.Provider
      value={{
        meta, ready: !!meta, range, setRange, facts, addFact, removeFact, clearFacts,
        exportSpec, openExport: setExportSpec, closeExport: () => setExportSpec(null),
        user, setUser,
      }}
    >
      {children}
    </Ctx.Provider>
  );
}
