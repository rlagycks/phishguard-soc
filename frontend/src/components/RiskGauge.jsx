import { useEffect, useState } from "react";
import { riskColor } from "../api/adapters.js";

export function RiskGauge({ score = 0, size = 132, stroke = 11, label = "최종 위험도" }) {
  const [value, setValue] = useState(0);
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const color = riskColor(score);

  useEffect(() => {
    const t = setTimeout(() => setValue(score || 0), 80);
    return () => clearTimeout(t);
  }, [score]);

  return (
    <div className="risk-gauge" style={{ width: size, height: size }}>
      <svg width={size} height={size}>
        <circle cx={size / 2} cy={size / 2} r={r} stroke="var(--surface-2)" strokeWidth={stroke} fill="none" />
        <circle
          className="risk-gauge-ring"
          cx={size / 2}
          cy={size / 2}
          r={r}
          stroke={color}
          strokeWidth={stroke}
          fill="none"
          strokeLinecap="round"
          strokeDasharray={c}
          strokeDashoffset={c * (1 - value)}
        />
      </svg>
      <div className="risk-gauge-label">
        <strong className="mono" style={{ color, fontSize: size * 0.26 }}>{score.toFixed(2)}</strong>
        <span>{label}</span>
      </div>
    </div>
  );
}
