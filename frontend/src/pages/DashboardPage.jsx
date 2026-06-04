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
  const rows = [
    ["danger", "위험 · 격리", stats?.quarantined || 0],
    ["warn", "의심 · 검토", stats?.review || 0],
    ["ok", "정상 · 통과", stats?.normal || 0]
  ];
  return (
    <section className="card panel-card">
      <h2>위험도 분포</h2>
      <div className="distribution">
        <div className="donut"><strong className="mono">{total}</strong><span>분석 메일</span></div>
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
