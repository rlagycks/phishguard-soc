/* ============================================================
   SOC 대시보드 — 공통 UI 컴포넌트 / 아이콘
   window 에 export
   ============================================================ */
const { useState, useEffect, useRef, useMemo } = React;
const S = window.SOC;

/* ---------- 아이콘 (stroke 1.7) ---------- */
function Icon({ name, size = 18, className, style }) {
  const p = { width: size, height: size, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 1.7, strokeLinecap: "round", strokeLinejoin: "round", className, style };
  const paths = {
    grid: <><rect x="3" y="3" width="7" height="9" rx="1.5"/><rect x="14" y="3" width="7" height="5" rx="1.5"/><rect x="14" y="12" width="7" height="9" rx="1.5"/><rect x="3" y="16" width="7" height="5" rx="1.5"/></>,
    shield: <><path d="M12 3l7 3v5c0 4.5-3 8-7 10-4-2-7-5.5-7-10V6z"/><path d="M9 12l2 2 4-4"/></>,
    mail: <><rect x="3" y="5" width="18" height="14" rx="2.5"/><path d="m3.5 7 8 5.5L19.5 7"/></>,
    alert: <><path d="M12 9v4M12 17h.01"/><path d="M10.3 3.9 2.4 18a2 2 0 0 0 1.7 3h15.8a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/></>,
    list: <><path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01"/></>,
    chart: <><path d="M3 3v18h18"/><path d="M7 14l3-4 3 3 4-6"/></>,
    activity: <><path d="M3 12h4l2 6 4-14 2 8h6"/></>,
    search: <><circle cx="11" cy="11" r="7"/><path d="m20 20-3.2-3.2"/></>,
    bell: <><path d="M18 8a6 6 0 1 0-12 0c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.7 21a2 2 0 0 1-3.4 0"/></>,
    settings: <><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.6 1.6 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.6 1.6 0 0 0-2.7 1.1V21a2 2 0 1 1-4 0v-.1A1.6 1.6 0 0 0 7 19.4a1.6 1.6 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1A1.6 1.6 0 0 0 2.6 14H2.5a2 2 0 1 1 0-4h.1A1.6 1.6 0 0 0 4 7.6l-.1-.1a2 2 0 0 1 2.8-2.8l.1.1A1.6 1.6 0 0 0 9 4.6V4.5a2 2 0 1 1 4 0v.1a1.6 1.6 0 0 0 2.7 1.1l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.6 1.6 0 0 0-.3 1.8V9a1.6 1.6 0 0 0 1.5 1h.1a2 2 0 1 1 0 4h-.1a1.6 1.6 0 0 0-1.4 1z"/></>,
    quarantine: <><rect x="4" y="4" width="16" height="16" rx="3"/><path d="M9 9l6 6M15 9l-6 6"/></>,
    clock: <><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></>,
    cpu: <><rect x="6" y="6" width="12" height="12" rx="2"/><path d="M9 1v3M15 1v3M9 20v3M15 20v3M1 9h3M1 15h3M20 9h3M20 15h3"/></>,
    link: <><path d="M10 13a5 5 0 0 0 7 0l2-2a5 5 0 0 0-7-7l-1 1"/><path d="M14 11a5 5 0 0 0-7 0l-2 2a5 5 0 0 0 7 7l1-1"/></>,
    arrow: <><path d="M5 12h14M13 6l6 6-6 6"/></>,
    chevron: <><path d="m9 6 6 6-6 6"/></>,
    chevdown: <><path d="m6 9 6 6 6-6"/></>,
    x: <><path d="M18 6 6 18M6 6l12 12"/></>,
    check: <><path d="M20 6 9 17l-5-5"/></>,
    google: <><path d="M21.8 12.2c0-.7-.1-1.3-.2-1.9H12v3.7h5.5a4.7 4.7 0 0 1-2 3.1v2.6h3.3c1.9-1.8 3-4.4 3-7.5z" fill="#4285F4" stroke="none"/><path d="M12 22c2.7 0 5-.9 6.6-2.4l-3.3-2.6c-.9.6-2 1-3.3 1-2.6 0-4.8-1.7-5.5-4.1H3.1v2.6A10 10 0 0 0 12 22z" fill="#34A853" stroke="none"/><path d="M6.5 13.9a6 6 0 0 1 0-3.8V7.5H3.1a10 10 0 0 0 0 9z" fill="#FBBC05" stroke="none"/><path d="M12 5.9c1.5 0 2.8.5 3.8 1.5l2.9-2.9A10 10 0 0 0 3.1 7.5l3.4 2.6C7.2 7.7 9.4 5.9 12 5.9z" fill="#EA4335" stroke="none"/></>,
    flow: <><rect x="3" y="9" width="6" height="6" rx="1.5"/><rect x="15" y="3" width="6" height="6" rx="1.5"/><rect x="15" y="15" width="6" height="6" rx="1.5"/><path d="M9 12h3M12 12v-6h3M12 12v6h3"/></>,
    eye: <><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7z"/><circle cx="12" cy="12" r="3"/></>,
    refresh: <><path d="M3 12a9 9 0 0 1 15-6.7L21 8M21 3v5h-5"/><path d="M21 12a9 9 0 0 1-15 6.7L3 16M3 21v-5h5"/></>,
    logout: <><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9"/></>,
    filter: <><path d="M3 5h18l-7 8v6l-4-2v-4z"/></>,
    user: <><circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/></>,
    db: <><ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v6c0 1.7 3.6 3 8 3s8-1.3 8-3V5M4 11v6c0 1.7 3.6 3 8 3s8-1.3 8-3v-6"/></>,
    bolt: <><path d="M13 2 4 14h7l-1 8 9-12h-7z"/></>,
  };
  return <svg {...p}>{paths[name] || null}</svg>;
}

/* ---------- 로고 ---------- */
function Logo({ size = 30 }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
      <div style={{ width: size, height: size, borderRadius: 9, background: "linear-gradient(135deg,#4f8cff,#7c5cff)", display: "grid", placeItems: "center", boxShadow: "0 6px 18px rgba(79,140,255,.4)", flex: "none" }}>
        <Icon name="shield" size={size * 0.6} style={{ color: "#fff" }} />
      </div>
    </div>
  );
}

/* ---------- 위험도 색 헬퍼 ---------- */
function toneOf(status) { return S.STATUS_META[status].tone; }
function riskColor(score) {
  if (score >= 0.7) return "var(--danger)";
  if (score >= 0.4) return "var(--warn)";
  return "var(--ok)";
}

/* ---------- 상태 배지 ---------- */
function StatusBadge({ status, dot = true }) {
  const m = S.STATUS_META[status];
  return (
    <span className={"badge " + m.tone}>
      {dot && <span className={"dot " + m.tone} />}{m.ko}
    </span>
  );
}

/* ---------- 원형 위험도 게이지 ---------- */
function RiskGauge({ score, size = 132, stroke = 11, label = "최종 위험도" }) {
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const color = riskColor(score);
  const [anim, setAnim] = useState(0);
  useEffect(() => { const t = setTimeout(() => setAnim(score), 80); return () => clearTimeout(t); }, [score]);
  return (
    <div style={{ position: "relative", width: size, height: size }}>
      <svg width={size} height={size} style={{ transform: "rotate(-90deg)" }}>
        <circle cx={size / 2} cy={size / 2} r={r} stroke="var(--surface-2)" strokeWidth={stroke} fill="none" />
        <circle cx={size / 2} cy={size / 2} r={r} stroke={color} strokeWidth={stroke} fill="none"
          strokeLinecap="round" strokeDasharray={c} strokeDashoffset={c * (1 - anim)}
          style={{ transition: "stroke-dashoffset 1s cubic-bezier(.2,.7,.2,1)", filter: `drop-shadow(0 0 6px ${color})` }} />
      </svg>
      <div style={{ position: "absolute", inset: 0, display: "grid", placeItems: "center", textAlign: "center" }}>
        <div>
          <div className="mono" style={{ fontSize: size * 0.28, fontWeight: 700, color, lineHeight: 1 }}>{score.toFixed(2)}</div>
          <div style={{ fontSize: 11, color: "var(--text-3)", marginTop: 5 }}>{label}</div>
        </div>
      </div>
    </div>
  );
}

/* ---------- 점수 바 ---------- */
function ScoreBar({ value, label, weight, color, delay = 0 }) {
  const [w, setW] = useState(0);
  useEffect(() => { const t = setTimeout(() => setW(value), delay); return () => clearTimeout(t); }, [value, delay]);
  const c = color || riskColor(value);
  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 6 }}>
        <span style={{ fontSize: 13, color: "var(--text-2)", fontWeight: 500, whiteSpace: "nowrap" }}>
          {label}{weight && <span style={{ color: "var(--text-4)", fontSize: 11.5, marginLeft: 6 }}>가중치 {weight}</span>}
        </span>
        <span className="mono" style={{ fontSize: 14, fontWeight: 700, color: c }}>{value.toFixed(2)}</span>
      </div>
      <div style={{ height: 8, borderRadius: 6, background: "var(--surface-2)", overflow: "hidden" }}>
        <div style={{ width: (w * 100) + "%", height: "100%", background: c, borderRadius: 6, transition: "width .9s cubic-bezier(.2,.7,.2,1)", boxShadow: `0 0 8px ${c}` }} />
      </div>
    </div>
  );
}

/* ---------- 브랜드 글리프 (발신자 아바타) ---------- */
function SenderGlyph({ name, brand, status, size = 38 }) {
  const ch = (name || "?").trim()[0] || "?";
  const tone = toneOf(status);
  const colors = { danger: ["#3a1622", "var(--danger)"], warn: ["#3a2c12", "var(--warn)"], ok: ["#12302b", "var(--ok)"] };
  const [bg, fg] = colors[tone];
  return (
    <div style={{ width: size, height: size, borderRadius: 10, background: bg, color: fg, display: "grid", placeItems: "center", fontWeight: 700, fontSize: size * 0.42, flex: "none", border: `1px solid ${fg}33` }}>
      {ch}
    </div>
  );
}

/* ---------- KPI 통계 카드 ---------- */
function KpiCard({ icon, label, value, sub, tone, accent }) {
  const color = { danger: "var(--danger)", warn: "var(--warn)", ok: "var(--ok)", accent: "var(--accent)" }[tone || "accent"];
  return (
    <div className="card" style={{ padding: "15px 16px", display: "flex", flexDirection: "column", gap: 9, position: "relative", overflow: "hidden" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 6 }}>
        <span style={{ fontSize: 12.5, color: "var(--text-3)", fontWeight: 600, whiteSpace: "nowrap" }}>{label}</span>
        <div style={{ width: 28, height: 28, borderRadius: 8, background: "var(--surface-2)", display: "grid", placeItems: "center", color, flex: "none" }}>
          <Icon name={icon} size={15} />
        </div>
      </div>
      <div style={{ display: "flex", alignItems: "baseline", gap: 8, whiteSpace: "nowrap" }}>
        <span className="mono" style={{ fontSize: 30, fontWeight: 700, color: "var(--text-1)", lineHeight: 1 }}>{value}</span>
        {sub && <span style={{ fontSize: 12.5, color, fontWeight: 600 }}>{sub}</span>}
      </div>
      {accent && <div style={{ position: "absolute", left: 0, top: 0, bottom: 0, width: 3, background: color }} />}
    </div>
  );
}

/* ---------- 막대 차트 (시간별) ---------- */
function HourBars({ data, height = 120 }) {
  const max = Math.max(...data.map((d) => d.total));
  return (
    <div style={{ display: "flex", alignItems: "flex-end", gap: 3, height }}>
      {data.map((d, i) => (
        <div key={i} style={{ flex: 1, display: "flex", flexDirection: "column", justifyContent: "flex-end", gap: 1, height: "100%" }} title={`${d.hour}시 · 총 ${d.total}건`}>
          <div style={{ height: `${(d.quarantined / max) * 100}%`, background: "var(--danger)", borderRadius: "2px 2px 0 0", minHeight: d.quarantined ? 2 : 0 }} />
          <div style={{ height: `${(d.review / max) * 100}%`, background: "var(--warn)", minHeight: d.review ? 2 : 0 }} />
          <div style={{ height: `${(d.normal / max) * 100}%`, background: "#2a3a5e", borderRadius: "0 0 2px 2px", minHeight: 2 }} />
        </div>
      ))}
    </div>
  );
}

Object.assign(window, { Icon, Logo, StatusBadge, RiskGauge, ScoreBar, SenderGlyph, KpiCard, HourBars, toneOf, riskColor });
