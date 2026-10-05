import type { BackscatterAnalysisResult, ChangeAnalysisResult, ChangeType, GroundAnalysisResult, Place, SearchResult, Watch } from "@/types";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function get<T>(path: string): Promise<T> {
  let r: Response;
  try {
    r = await fetch(`${BASE}${path}`);
  } catch {
    throw new Error("Earth Pulse backend is offline. Start the backend at http://localhost:8000 and try again.");
  }
  if (!r.ok) {
    const body = await r.json().catch(() => ({}));
    throw new Error(body.detail ?? `Request failed (${r.status})`);
  }
  return r.json();
}

export const searchPlaces = (q: string) =>
  get<{ results: Place[] }>(`/api/locations/search?q=${encodeURIComponent(q)}`).then((r) => r.results);

export const searchNisar = (lat: number, lon: number, changeType: ChangeType, start?: string, end?: string) => {
  const p = new URLSearchParams({ lat: String(lat), lon: String(lon), change_type: changeType });
  if (start) p.set("start", start);
  if (end) p.set("end", end);
  return get<SearchResult>(`/api/nisar/search?${p}`);
};
export const analyzeChange = (lat: number, lon: number, product: string, start: string, end: string) =>
  send<ChangeAnalysisResult>("POST", "/api/analysis/compare", { lat, lon, product, start, end });
export const analyzeGround = (lat: number, lon: number) =>
  send<{ analysis_id: string; result: GroundAnalysisResult }>("POST", "/api/analysis", { lat, lon, change_type: "ground" });
export const analyzeBackscatter = (lat: number, lon: number, product: "GCOV" | "GSLC", before?: string, after?: string, polarization?: string) =>
  send<{ analysis_id: string; result: BackscatterAnalysisResult }>("POST", "/api/analysis/backscatter",
    { lat, lon, product, before_granule_id: before, after_granule_id: after, polarization });

async function send<T>(method: string, path: string, body?: unknown): Promise<T> {
  let r: Response;
  try {
    r = await fetch(`${BASE}${path}`, { method, headers: { "Content-Type": "application/json" }, body: body ? JSON.stringify(body) : undefined });
  } catch {
    throw new Error("Earth Pulse backend is offline. Start the backend at http://localhost:8000 and try again.");
  }
  if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail ?? `Request failed (${r.status})`);
  return r.json();
}
export const createWatch = (lat: number, lon: number, change_type: ChangeType) => send<Watch>("POST", "/api/watches", { lat, lon, change_type });
export const listWatches = () => get<{ watches: Watch[] }>("/api/watches").then((r) => r.watches);
export const checkWatch = (id: number) => send<Watch>("POST", `/api/watches/${id}/check`);
export const readWatch = (id: number) => send("POST", `/api/watches/${id}/read`);
export const deleteWatch = (id: number) => send("DELETE", `/api/watches/${id}`);
