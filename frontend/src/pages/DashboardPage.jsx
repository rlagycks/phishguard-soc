import { useEffect, useMemo, useState } from "react";
import { fetchEmails, fetchHourlyStats, fetchStats, fetchSystemHealth } from "../api/client.js";
import { EmailTable } from "../components/EmailTable.jsx";
import { KpiCard } from "../components/KpiCard.jsx";

export function DashboardPage({ live, onSelect }) {
  const [stats, setStats] = useState(null);
  const [emails, setEmails] = useState([]);
  const [hourly, setHourly] = useState([]);
  const [health, setHealth] = useState([]);
  const [error, setError] = useState("");

  async function load() {
    try {
      setError("");
      const [nextStats, nextEmails, nextHourly, nextHealth] = await Promise.all([
        fetchStats(),
        fetchEmails({ limit: 50 }),
        fetchHourlyStats(),
        fetchSystemHealth()
      ]);
      setStats(nextStats);
      setEmails(nextEmails);
      setHourly(nextHourly);
      setHealth(nextHealth.items || []);
    } catch (err) {
      setError(err.message);
    }
  }

  useEffect(() => {
    load();
  }, []);

  useEffect(() => {
    if (!live) return undefined;
    const id = setInterval(load, 10000);
    return () => clearInterval(id);
  }, [live]);

  const kpis = useMemo(() => [
    { icon: "mail", label: "분석 메일", value: stats?.total ?? "-", sub: "건", tone: "accent" },
    { icon: "quarantine", label: "자동 격리", value: stats?.quarantined ?? "-", sub: "위험", tone: "danger" },
    { icon: "eye", label: "검토 대기", value: stats?.review ?? "-", sub: "의심", tone: "warn" },
    { icon: "clock", label: "평균 처리", value: stats ? stats.avgSeconds.toFixed(1) : "-", sub: "초", tone: "ok" }
  ], [stats]);

  return (
    <div className="dashboard-grid">
      {error && <div className="error-state wide">{error}</div>}
      <div className="kpi-grid">{kpis.map((item) => <KpiCard key={item.label} {...item} />)}</div>
      <section className="card live-panel">
        <div className="panel-head">
          <div><span className="live-dot" /><h2>실시간 탐지 현황</h2></div>
          <small>최근 {emails.length}건</small>
        </div>
        <EmailTable emails={emails} onSelect={onSelect} compact />
      </section>
      <aside className="side-stack">
        <Distribution stats={stats} />
        <SystemHealth items={health} />
        <HourlyMini data={hourly} />
      </aside>
    </div>
  );
}

function Distribution({ stats }) {
  const total = stats?.total || 0;
  const quarantined = stats?.quarantined || 0;
  const review = stats?.review || 0;
  const normal = stats?.normal || 0;

  const dangerPct = total > 0 ? (quarantined / total) * 100 : 0;
  const warnPct = total > 0 ? (review / total) * 100 : 0;
  const p1 = dangerPct.toFixed(1);
  const p2 = (dangerPct + warnPct).toFixed(1);
  const donutStyle = total > 0
    ? { background: `conic-gradient(var(--danger) 0 ${p1}%, var(--warn) ${p1}% ${p2}%, #2a3a5e ${p2}% 100%)` }
    : { background: "#2a3a5e" };

  const rows = [
    ["danger", "위험 · 격리", quarantined],
    ["warn", "의심 · 검토", review],
    ["ok", "정상 · 통과", normal]
  ];
  return (
    <section className="card panel-card">
      <h2>위험도 분포</h2>
      <div className="distribution">
        <div className="donut" style={donutStyle}>
          <strong className="mono">{total}</strong><span>분석 메일</span>
        </div>
        <div>
          {rows.map(([tone, label, value]) => (
            <p key={label}><span className={`dot ${tone}`} />{label}<b className="mono">{value}</b></p>
          ))}
        </div>
      </div>
    </section>
  );
}

function SystemHealth({ items }) {
  return (
    <section className="card panel-card">
      <h2>시스템 상태</h2>
      <div className="health-list">
        {items.map((item) => (
          <p key={item.label}>
            <span className={`dot ${item.tone || "ok"}`} />
            <span>{item.label}</span>
            <b>{item.value}</b>
            <small className="mono">{item.detail}</small>
          </p>
        ))}
      </div>
    </section>
  );
}

function HourlyMini({ data }) {
  const max = Math.max(1, ...data.map((row) => row.total || 0));
  return (
    <section className="card panel-card">
      <h2>시간대별 탐지량</h2>
      <div className="hour-bars">
        {data.map((row) => (
          <span key={row.hour} title={`${row.hour}시 · ${row.total}건`} style={{ height: `${Math.max(5, (row.total / max) * 100)}%` }} />
        ))}
      </div>
    </section>
  );
}
