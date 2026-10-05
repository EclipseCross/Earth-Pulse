import type { Watch } from "@/types";

interface Props {
  watches: Watch[];
  onFocus: (w: Watch) => void;
  onCheck: (id: number) => void;
  onRead: (id: number) => void;
  onDelete: (id: number) => void;
}

export default function WatchList({ watches, onFocus, onCheck, onRead, onDelete }: Props) {
  if (!watches.length) return <p className="hint">No watched areas yet. Select a place and choose Watch this area.</p>;
  return (
    <ul className="watches">
      {watches.map((w) => (
        <li key={w.id}>
          <button className="link" onClick={() => onFocus(w)}>{w.lat.toFixed(3)}, {w.lon.toFixed(3)} ({w.change_type})</button>
          {w.unread > 0 && <span className="badge">{w.unread} new</span>}
          <small>
            {w.last_error ? `Last check failed: ${w.last_error}` :
              `Baseline ${w.baseline_count} observations. Checked ${w.last_checked ? new Date(w.last_checked * 1000).toLocaleString() : "never"}.`}
          </small>
          {w.new_observations.slice(0, 3).map((n) => (
            <small key={n.granule_id}>New {n.product}: acquired {n.acquisition_start?.slice(0, 10) ?? "unknown"}</small>
          ))}
          <span className="row">
            <button className="mini" onClick={() => onCheck(w.id)}>Check now</button>
            {w.unread > 0 && <button className="mini" onClick={() => onRead(w.id)}>Mark read</button>}
            <button className="mini" onClick={() => onDelete(w.id)}>Remove</button>
          </span>
        </li>
      ))}
    </ul>
  );
}
