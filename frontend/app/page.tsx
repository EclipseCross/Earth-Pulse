"use client";
import dynamic from "next/dynamic";
import { useCallback, useEffect, useState } from "react";
import ChangeTypeSelect from "@/components/ChangeType/ChangeTypeSelect";
import ObservationList from "@/components/Analysis/ObservationList";
import WatchList from "@/components/Watch/WatchList";
import { analyzeChange, checkWatch, createWatch, deleteWatch, listWatches, readWatch, searchNisar, searchPlaces } from "@/services/api";
import type { ChangeAnalysisResult, ChangeType, SearchResult, Watch } from "@/types";

const EarthMap = dynamic(() => import("@/components/Map/EarthMap"), { ssr: false });

export default function Home() {
  const [q, setQ] = useState("");
  const [pt, setPt] = useState<{ lat: number; lon: number } | null>(null);
  const [type, setType] = useState<ChangeType>("ground");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [busy, setBusy] = useState("");
  const [err, setErr] = useState("");
  const [res, setRes] = useState<SearchResult | null>(null);
  const [analysisProduct, setAnalysisProduct] = useState("GCOV");
  const [analysis, setAnalysis] = useState<ChangeAnalysisResult | null>(null);
  const [watches, setWatches] = useState<Watch[]>([]);

  const refresh = useCallback(() => listWatches().then(setWatches).catch(() => {}), []);
  useEffect(() => { refresh(); const t = setInterval(refresh, 60000); return () => clearInterval(t); }, [refresh]);

  async function act(fn: () => Promise<unknown>, label: string) {
    setErr(""); setBusy(label);
    try { await fn(); await refresh(); } catch (e) { setErr((e as Error).message); } finally { setBusy(""); }
  }

  async function find() {
    setErr("");
    try {
      setBusy("Searching places...");
      const r = await searchPlaces(q);
      if (!r.length) throw new Error("No place found. Try coordinates like 23.8103, 90.4125.");
      setPt({ lat: r[0].lat, lon: r[0].lon });
    } catch (e) { setErr((e as Error).message); } finally { setBusy(""); }
  }

  async function run() {
    if (!pt) return;
    setErr(""); setRes(null);
    try {
      setBusy("Searching NISAR...");
      setRes(await searchNisar(pt.lat, pt.lon, type, start || undefined, end || undefined));
    } catch (e) { setErr((e as Error).message); } finally { setBusy(""); }
  }

  async function runAnalysis() {
    if (!pt || !start || !end) return;
    setErr(""); setAnalysis(null);
    try {
      setBusy("Downloading and comparing NISAR data...");
      setAnalysis(await analyzeChange(pt.lat, pt.lon, analysisProduct, start, end));
    } catch (e) { setErr((e as Error).message); } finally { setBusy(""); }
  }

  return (
    <main className="shell">
      <aside className="panel">
        <h1>Earth Pulse</h1>
        <p className="tag">Understand how Earth changes.</p>
        <form onSubmit={(e) => { e.preventDefault(); find(); }}>
          <label htmlFor="q">Place or coordinates</label>
          <input id="q" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Dhaka, or 23.8103, 90.4125" />
        </form>
        <p className="hint">Or click anywhere on the map.</p>
        {pt && <p className="coords">{pt.lat.toFixed(4)}, {pt.lon.toFixed(4)}</p>}
        <ChangeTypeSelect value={type} onChange={setType} />
        <div className="dates">
          <label>From <input type="date" value={start} onChange={(e) => setStart(e.target.value)} /></label>
          <label>To <input type="date" value={end} onChange={(e) => setEnd(e.target.value)} /></label>
        </div>
        <button className="go" disabled={!pt || !!busy} onClick={run}>Search NISAR observations</button>
        <button className="go alt" disabled={!pt || !!busy}
          onClick={() => pt && act(() => createWatch(pt.lat, pt.lon, type), "Recording baseline observations...")}>Watch this area</button>
        <label className="analysis-control">Analyze product
          <select value={analysisProduct} onChange={(e) => setAnalysisProduct(e.target.value)}>
            <option value="GUNW">GUNW · ground deformation</option>
            <option value="GSLC">GSLC · radar surface response</option>
            <option value="GCOV">GCOV · land and water response</option>
            <option value="GOFF">GOFF · pixel movement</option>
            <option value="SME2">SME2 · soil moisture</option>
          </select>
        </label>
        <button className="go alt" disabled={!pt || !start || !end || !!busy} onClick={runAnalysis}>
          Analyze change between dates
        </button>
        {busy && <p className="busy">{busy}</p>}
        {err && <p className="err" role="alert">{err}</p>}
        {res && <ObservationList result={res} />}
        {analysis && <section className="analysis-result" aria-live="polite">
          <h3>Possible change detected</h3>
          <p>{analysis.interpretation}</p>
          <small>{analysis.baseline_date} → {analysis.comparison_date} · {analysis.metric}: {analysis.value.toFixed(3)} {analysis.unit}</small>
          <p className="hint">This is an automated screening result, not a confirmed event. Product-specific quality and geolocation masks are still required.</p>
        </section>}
        <h3>Watched areas</h3>
        <p className="hint">Checked automatically for new NISAR observations. NISAR products appear 1 to 3 days after acquisition, so this is near-real-time, not live.</p>
        <WatchList watches={watches} onFocus={(w) => setPt({ lat: w.lat, lon: w.lon })}
          onCheck={(id) => act(() => checkWatch(id), "Checking NASA for new observations...")}
          onRead={(id) => act(() => readWatch(id), "Updating...")}
          onDelete={(id) => act(() => deleteWatch(id), "Removing...")} />
        <p className="foot">Independent Space Apps project. Not an official NASA application. Change analysis is an automated screening result and not a confirmed event.</p>
      </aside>
      <EarthMap selected={pt} onSelect={(lat, lon) => setPt({ lat, lon })} />
    </main>
  );
}
