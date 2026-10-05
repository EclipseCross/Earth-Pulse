import type { SearchResult } from "@/types";

export default function ObservationList({ result }: { result: SearchResult }) {
  return (
    <section aria-live="polite">
      <h3>{result.count} NISAR observation{result.count === 1 ? "" : "s"} found</h3>
      <p className="origin">
        {result.origin === "demo" ? "Demo mode: using preprocessed NISAR data." : "Live search of NASA Earthdata (metadata only)."}
      </p>
      {result.notes.map((n) => <p key={n} className="note">{n}</p>)}
      <ul>
        {result.observations.map((o) => (
          <li key={o.granule_id}>
            <b>{o.product}</b> {o.acquisition_start?.slice(0, 10) ?? "date unknown"}
            <small>{o.granule_id}</small>
          </li>
        ))}
      </ul>
    </section>
  );
}
