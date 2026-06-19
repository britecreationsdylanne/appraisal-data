const BASE = "/api";

export function currentUser(): string {
  return localStorage.getItem("adr_user") || "local";
}
export function setCurrentUser(name: string) {
  localStorage.setItem("adr_user", name.trim() || "local");
}

function headers(json = false): Record<string, string> {
  const h: Record<string, string> = { "X-User": currentUser() };
  if (json) h["Content-Type"] = "application/json";
  return h;
}

async function post<T = any>(path: string, body: any): Promise<T> {
  const r = await fetch(BASE + path, { method: "POST", headers: headers(true), body: JSON.stringify(body) });
  if (!r.ok) throw new Error((await r.text()) || r.statusText);
  return r.json();
}

async function patch<T = any>(path: string, body: any): Promise<T> {
  const r = await fetch(BASE + path, { method: "PATCH", headers: headers(true), body: JSON.stringify(body) });
  if (!r.ok) throw new Error((await r.text()) || r.statusText);
  return r.json();
}

async function get<T = any>(path: string): Promise<T> {
  const r = await fetch(BASE + path, { headers: headers() });
  if (!r.ok) throw new Error(r.statusText);
  return r.json();
}

async function del<T = any>(path: string): Promise<T> {
  const r = await fetch(BASE + path, { method: "DELETE", headers: headers() });
  if (!r.ok) throw new Error(r.statusText);
  return r.json();
}

export interface DateRange {
  start: string;
  end: string;
  granularity: string;
}

export const api = {
  meta: () => get("/meta"),
  chat: (question: string, dr: DateRange) =>
    post("/chat", { question, date_start: dr.start, date_end: dr.end }),
  chatHistory: () => get("/chat/history"),
  chatLibrary: () => get("/chat/library"),
  shareChat: (id: number, shared: boolean) => post(`/chat/${id}/share`, { shared }),
  deleteChat: (id: number) => del(`/chat/${id}`),
  clearChatHistory: () => del("/chat/history"),

  // generic saved items (trends + images)
  savedItems: (kind: string) => get(`/saved?kind=${kind}`),
  savedLibrary: (kind: string) => get(`/saved/library?kind=${kind}`),
  createSaved: (item: { kind: string; title: string; summary?: string; payload?: any; shared?: boolean }) =>
    post("/saved", item),
  shareSaved: (id: number, shared: boolean) => post(`/saved/${id}/share`, { shared }),
  deleteSaved: (id: number) => del(`/saved/${id}`),
  trends: (dimension: string, value: string, dr: DateRange) =>
    post("/trends", { dimension, value, date_start: dr.start, date_end: dr.end, granularity: dr.granularity }),
  templates: () => get("/templates"),
  createTemplate: (name: string, description: string, spec: any) =>
    post("/templates", { name, description, spec }),
  updateTemplate: (id: number, body: { name?: string; description?: string; spec?: any }) =>
    patch(`/templates/${id}`, body),
  duplicateTemplate: (id: number) => post(`/templates/${id}/duplicate`, {}),
  shareTemplate: (id: number, shared: boolean) => post(`/templates/${id}/share`, { shared }),
  deleteTemplate: (id: number) => del(`/templates/${id}`),
  runTemplate: (id: number, dr: DateRange, save = true) =>
    post(`/templates/${id}/run`, { date_start: dr.start, date_end: dr.end, granularity: dr.granularity, save }),
  previewSpec: (spec: any, dr: DateRange) =>
    post("/reports/preview", { spec, date_start: dr.start, date_end: dr.end, granularity: dr.granularity }),
  runs: () => get("/runs"),
  run: (id: number) => get(`/runs/${id}`),
  analyze: (id: number) => post(`/runs/${id}/analyze`, {}),
  shareRun: (id: number, shared: boolean) => post(`/runs/${id}/share`, { shared }),
  deleteRun: (id: number) => del(`/runs/${id}`),
  factFinder: (text: string) => post("/factfinder/analyze", { text }),

  exportSizes: () => get("/export/sizes"),
  exportSvg: (spec: any, size: string) => post("/export", { spec, size }),
  exportEdit: (spec: any, instruction: string, size: string) =>
    post("/export/edit", { spec, instruction, size }),
};
