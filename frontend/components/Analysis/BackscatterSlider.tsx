"use client";

import { useState } from "react";
import type { BackscatterAnalysisResult } from "@/types";

export default function BackscatterSlider({ result }: { result: BackscatterAnalysisResult }) {
  const [divider, setDivider] = useState(50);
  return (
    <section className="analysis-result" aria-label="Before and after backscatter comparison">
      <h3>Potential land-surface disturbance</h3>
      <div className="comparison-slider">
        <div className="comparison-after" style={{ width: `${divider}%` }}>
          <strong>After · {result.after_date ?? "unknown date"}</strong>
          <span>{result.product} · {result.polarization}</span>
        </div>
        <div className="comparison-before">
          <strong>Before · {result.before_date ?? "unknown date"}</strong>
          <span>{result.product} · {result.polarization}</span>
        </div>
      </div>
      <label>Before / after divider
        <input type="range" min="0" max="100" value={divider} onChange={(e) => setDivider(Number(e.target.value))} />
      </label>
      {result.status === "insufficient" ? <p className="note">{result.message}</p> : (
        <p>Mean change {result.mean_db_change?.toFixed(2)} dB · affected {result.affected_area_km2?.toFixed(3)} km² · valid {(result.valid_fraction * 100).toFixed(1)}%</p>
      )}
      <small>Screening rule: {result.statistical_rule}. Values are radar backscatter, not photographs.</small>
      <p className="hint">Potential land-surface disturbance, not a confirmed event.</p>
      <ul>{result.limitations.map((item) => <li key={item}><small>{item}</small></li>)}</ul>
    </section>
  );
}
