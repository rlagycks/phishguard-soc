import { STATUS_META } from "../api/adapters.js";

export function StatusBadge({ status, dot = true }) {
  const meta = STATUS_META[status] || STATUS_META.pending;
  return (
    <span className={`badge ${meta.tone}`}>
      {dot && <span className={`dot ${meta.tone}`} />}
      {meta.label}
    </span>
  );
}
