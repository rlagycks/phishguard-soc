import { riskColor } from "../api/adapters.js";

export function ScoreBar({ label, value = 0, weight }) {
  const color = riskColor(value);
  return (
    <div className="score-bar">
      <div className="score-bar-head">
        <span>
          {label}
          {weight && <small>가중치 {weight}</small>}
        </span>
        <b className="mono" style={{ color }}>{value.toFixed(2)}</b>
      </div>
      <div className="score-track">
        <div className="score-fill" style={{ width: `${value * 100}%`, background: color }} />
      </div>
    </div>
  );
}
