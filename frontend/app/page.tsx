"use client";
import dynamic from "next/dynamic";
import { useCallback, useEffect, useState } from "react";
import ChangeTypeSelect from "@/components/ChangeType/ChangeTypeSelect";
import ObservationList from "@/components/Analysis/ObservationList";
import WatchList from "@/components/Watch/WatchList";
import { analyzeBackscatter, analyzeChange, analyzeGround, checkWatch, createWatch, deleteWatch, listWatches, readWatch, searchNisar, searchPlaces } from "@/services/api";
import BackscatterSlider from "@/components/Analysis/BackscatterSlider";
import type { BackscatterAnalysisResult, ChangeAnalysisResult, ChangeType, GroundAnalysisResult, SearchResult, Watch } from "@/types";

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
  const [ground, setGround] = useState<GroundAnalysisResult | null>(null);
  const [backscatter, setBackscatter] = useState<BackscatterAnalysisResult | null>(null);
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

  async function runGround() {
    if (!pt) return;
    setErr(""); setGround(null);
    try {
      setBusy("Searching NISAR");
      setBusy("Retrieving observations");
      const response = await analyzeGround(pt.lat, pt.lon);
      setBusy("Processing radar data");
      setGround(response.result);
      setBusy("Detecting surface change");
    } catch (e) { setErr((e as Error).message); } finally { setBusy(""); }
  }

  async function runBackscatter() {
    if (!pt || (analysisProduct !== "GCOV" && analysisProduct !== "GSLC")) return;
    setErr(""); setBackscatter(null);
    try {
      setBusy("Searching paired NISAR acquisitions");
      const response = await analyzeBackscatter(pt.lat, pt.lon, analysisProduct);
      setBusy("Converting radar backscatter to dB");
      setBackscatter(response.result);
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
          <label>From <input type="date" min="2026-06-17" value={start} onChange={(e) => setStart(e.target.value)} /></label>
          <label>To <input type="date" min="2026-06-17" value={end} onChange={(e) => setEnd(e.target.value)} /></label>
        </div>
        <p className="hint">Public NISAR records currently begin around June 17, 2026.</p>
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
        {(analysisProduct === "GCOV" || analysisProduct === "GSLC") &&
          <button className="go" disabled={!pt || !!busy} onClick={runBackscatter}>Analyze backscatter change</button>}
        {analysisProduct === "GUNW" && <button className="go" disabled={!pt || !!busy} onClick={runGround}>Analyze ground movement</button>}
        {busy && <p className="busy">{busy}</p>}
        {err && <p className="err" role="alert">{err}</p>}
        {res && <ObservationList result={res} />}
        {analysis && <section className="analysis-result" aria-live="polite">
          <h3>Possible change detected</h3>
          <p>{analysis.interpretation}</p>
          <small>{analysis.baseline_date} → {analysis.comparison_date} · {analysis.metric}: {analysis.value.toFixed(3)} {analysis.unit}</small>
          <p className="hint">This is an automated screening result, not a confirmed event. Product-specific quality and geolocation masks are still required.</p>
        </section>}
        {ground && <section className="analysis-result" aria-live="polite">
          <h3>Ground movement screening</h3>
          <p>Line-of-sight displacement relative to a reference area. Not vertical motion and not structural damage.</p>
          {ground.status === "insufficient" ? <p className="note">{ground.message}</p> : <>
            <p>Mean {ground.mean?.toFixed(2)} mm · range {ground.min?.toFixed(2)} to {ground.max?.toFixed(2)} mm · affected {ground.affected_area_km2?.toFixed(3)} km²</p>
            <p>Valid {(ground.valid_fraction * 100).toFixed(1)}% · coherence {ground.coherence_mean?.toFixed(2)} · confidence {ground.confidence}</p>
          </>}
          <small>{ground.reference_acquisition_date} → {ground.secondary_acquisition_date} · {ground.sign_convention}</small>
          <p className="hint">NASA-ISRO NISAR · GUNW · Earth Pulse pipeline</p>
          <ul>{ground.limitations.map((item) => <li key={item}><small>{item}</small></li>)}</ul>
        </section>}
        {backscatter && <BackscatterSlider result={backscatter} />}
        <h3>Watched areas</h3>
        <p className="hint">Checked automatically for new NISAR observations. NISAR products appear 1 to 3 days after acquisition, so this is near-real-time, not live.</p>
        <WatchList watches={watches} onFocus={(w) => setPt({ lat: w.lat, lon: w.lon })}
          onCheck={(id) => act(() => checkWatch(id), "Checking NASA for new observations...")}
          onRead={(id) => act(() => readWatch(id), "Updating...")}
          onDelete={(id) => act(() => deleteWatch(id), "Removing...")} />
        <p className="foot">Independent Space Apps project. Not an official NASA application. Change analysis is an automated screening result and not a confirmed event.</p>
      </aside>
      <EarthMap selected={pt} onSelect={(lat, lon) => setPt({ lat, lon })} zones={ground?.zones} />
    </main>
  );
}
