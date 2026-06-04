import { useEffect, useState } from "react";
import { fetchActionLogs } from "../api/client.js";
import { formatTime, riskColor } from "../api/adapters.js";
import { Icon } from "../components/Icon.jsx";

export function LogsPage({ onSelect }) {
  const [logs, setLogs] = useState([]);

  useEffect(() => {
    fetchActionLogs().then(setLogs);
  }, []);

  return (
    <section className="card logs-card">
      <header>
        <Icon name="activity" size={18} />
        <h2>자동 대응 로그</h2>
        <span className="badge ghost">Action Engine</span>
        <small>{logs.length}건 · 감사 추적용 보존</small>
      </header>
      <div className="log-list">
        {logs.map((log) => (
          <button key={`${log.id}-${log.ts}`} onClick={() => onSelect(log.id)}>
            <span className="mono">{formatTime(log.ts)}</span>
            <span className={`dot ${log.tone}`} />
            <strong>{log.subject}</strong>
            <span>{log.action}</span>
            <b className="mono" style={{ color: riskColor(log.final_score || 0) }}>{Number(log.final_score || 0).toFixed(2)}</b>
          </button>
        ))}
      </div>
    </section>
  );
}
