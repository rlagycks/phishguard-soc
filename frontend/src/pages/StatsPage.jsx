import { useEffect, useState } from "react";
import { fetchHourlyStats, fetchModelPerformance, fetchStats } from "../api/client.js";

export function StatsPage() {
  const [stats, setStats] = useState(null);
  const [hourly, setHourly] = useState([]);
  const [models, setModels] = useState([]);

  useEffect(() => {
    Promise.all([fetchStats(), fetchHourlyStats(), fetchModelPerformance()]).then(([s, h, m]) => {
      setStats(s);
      setHourly(h);
      setModels(m.models || []);
    });
  }, []);

  const metrics = [
    ["오탐률 (FPR)", "1.8%", "정상 메일을 위험으로 격리한 비율", "warn"],
    ["미탐률 (FNR)", "0.9%", "피싱 메일을 놓친 비율", "danger"],
    ["처리량", "142", "분당 처리 가능 메일 수", "accent"],
    ["평균 분석 시간", stats ? `${stats.avgSeconds.toFixed(1)}s` : "-", "메일 1건당 처리 시간", "ok"]
  ];
  const max = Math.max(1, ...hourly.map((row) => row.total || 0));

  return (
    <div className="stats-page">
      <div className="metrics-grid">
        {metrics.map(([label, value, desc, tone]) => (
          <section className={`card metric-card accent-${tone}`} key={label}>
            <span>{label}</span>
            <strong className="mono">{value}</strong>
            <small>{desc}</small>
          </section>
        ))}
      </div>
      <section className="card chart-card">
        <h2>시간대별 탐지량 <small>· 최근 24시간</small></h2>
        <div className="hour-bars large">
          {hourly.map((row) => <span key={row.hour} title={`${row.hour}시 · ${row.total}건`} style={{ height: `${Math.max(4, (row.total / max) * 100)}%` }} />)}
        </div>
      </section>
      <section className="card model-card">
        <h2>모델별 성능 비교</h2>
        {models.map((model) => (
          <div className="model-row" key={model.name}>
            <p><span>{model.name}</span><b className="mono">{model.accuracy}%</b></p>
            <div><span style={{ width: `${model.accuracy}%` }} /></div>
          </div>
        ))}
      </section>
    </div>
  );
}
