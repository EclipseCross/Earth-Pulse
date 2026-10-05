import type { SearchResult } from "@/types";

export default function ObservationList({ result }: { result: SearchResult }) {
  return (
    <section aria-live="polite">
      <h3>{result.count} NISAR observation{result.count === 1 ? "" : "s"} found</h3>
      <p className="origin">
        {result.origin === "demo" ? "Demo mode: using preprocessed NISAR data." : "Live search of NASA Earthdata (metadata only)."}
      </p>
      {result.notes.map((n) => <p key={n} className="note">{n}</p>)}
      {result.observations.length === 0 ? (
        <p className="note">No matching observations were published for this location and date range. The public NISAR catalog currently starts around June 17, 2026; try a later range and a broader area.</p>
      ) : (
        <ul>
          {result.observations.map((o) => (
            <li key={o.granule_id}>
              <b>{o.product}</b> {o.acquisition_start?.slice(0, 10) ?? "date unknown"}
              <small>{o.granule_id}</small>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
