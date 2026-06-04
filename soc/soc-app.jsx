/* ============================================================
   SOC 대시보드 — 앱 셸 / 라우팅 / 라이브 시뮬레이션
   ============================================================ */

const NAV = [
  { key: "dashboard", label: "대시보드", icon: "grid" },
  { key: "list", label: "위험 메일 목록", icon: "list" },
  { key: "logs", label: "자동 대응 로그", icon: "activity" },
  { key: "stats", label: "통계 / 성능", icon: "chart" },
];
const ROUTE_TITLE = {
  dashboard: ["실시간 탐지 현황", "메일 수신 이벤트를 트리거로 자동 분석·격리합니다"],
  list: ["위험 메일 목록", "최종 위험도 기준으로 정렬·필터링합니다"],
  logs: ["자동 대응 로그", "Quarantine / Needs-Review / Normal 처리 내역"],
  stats: ["통계 / 성능", "탐지 성능, 처리 시간, 모델별 비교 지표"],
};

/* ---------- 사이드바 ---------- */
function Sidebar({ route, setRoute, onLogout }) {
  return (
    <aside style={{ width: "var(--sidebar-w)", background: "var(--bg-0)", borderRight: "1px solid var(--line-soft)", display: "flex", flexDirection: "column", flex: "none" }}>
      <div style={{ padding: "20px 18px 22px", display: "flex", alignItems: "center", gap: 11, borderBottom: "1px solid var(--line-soft)" }}>
        <Logo size={34} />
        <div>
          <div style={{ fontWeight: 800, fontSize: 16, color: "var(--text-1)", letterSpacing: "-.02em", lineHeight: 1.1 }}>PhishGuard <span style={{ color: "var(--accent)" }}>SOC</span></div>
          <div style={{ fontSize: 11, color: "var(--text-4)" }}>Security Automation</div>
        </div>
      </div>
      <nav style={{ padding: "16px 12px", display: "flex", flexDirection: "column", gap: 3, flex: 1 }}>
        <div style={{ fontSize: 10.5, fontWeight: 700, color: "var(--text-4)", textTransform: "uppercase", letterSpacing: ".08em", padding: "8px 12px 6px" }}>관제</div>
        {NAV.map((n) => {
          const active = route === n.key;
          return (
            <button key={n.key} onClick={() => setRoute(n.key)} style={{ display: "flex", alignItems: "center", gap: 11, padding: "10px 12px", borderRadius: 10, border: "none", background: active ? "var(--accent-soft)" : "transparent", color: active ? "var(--text-1)" : "var(--text-3)", fontSize: 13.5, fontWeight: active ? 600 : 500, textAlign: "left", position: "relative", transition: "background .15s, color .15s" }}
              onMouseEnter={(e) => { if (!active) e.currentTarget.style.color = "var(--text-1)"; }}
              onMouseLeave={(e) => { if (!active) e.currentTarget.style.color = "var(--text-3)"; }}>
              {active && <span style={{ position: "absolute", left: 0, top: 9, bottom: 9, width: 3, borderRadius: 3, background: "var(--accent)" }} />}
              <Icon name={n.icon} size={18} style={{ color: active ? "var(--accent)" : "inherit" }} />{n.label}
            </button>
          );
        })}
      </nav>
      <div style={{ padding: 12, borderTop: "1px solid var(--line-soft)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "8px 10px", borderRadius: 10, background: "var(--surface-1)" }}>
          <div style={{ width: 32, height: 32, borderRadius: 8, background: "linear-gradient(135deg,#4f8cff,#7c5cff)", display: "grid", placeItems: "center", color: "#fff", fontWeight: 700, fontSize: 13 }}>S</div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontSize: 12.5, color: "var(--text-1)", fontWeight: 600, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>soc-analyst</div>
            <div className="mono" style={{ fontSize: 10.5, color: "var(--text-4)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>phishing-report@gmail.com</div>
          </div>
          <button className="btn ghost sm" onClick={onLogout} title="로그아웃" style={{ padding: 7, width: 30, height: 30 }}><Icon name="logout" size={15} /></button>
        </div>
      </div>
    </aside>
  );
}

/* ---------- 레이아웃 토글 ---------- */
function LayoutSwitch({ layout, setLayout }) {
  const opts = [["A", "클래식"], ["B", "라이브"], ["C", "벤토"]];
  return (
    <div style={{ display: "flex", gap: 3, background: "var(--surface-1)", padding: 3, borderRadius: 9, border: "1px solid var(--line-soft)" }} title="대시보드 레이아웃 변형">
      {opts.map(([k, l]) => (
        <button key={k} onClick={() => setLayout(k)} style={{ border: "none", background: layout === k ? "var(--accent)" : "transparent", color: layout === k ? "#061021" : "var(--text-3)", padding: "6px 11px", borderRadius: 6, fontSize: 12, fontWeight: 700 }}>{l}</button>
      ))}
    </div>
  );
}

/* ---------- 토스트 ---------- */
function Toast({ msg }) {
  if (!msg) return null;
  return (
    <div style={{ position: "fixed", bottom: 24, left: "50%", transform: "translateX(-50%)", zIndex: 60, background: "var(--surface-3)", border: "1px solid var(--line)", borderRadius: 12, padding: "12px 18px", boxShadow: "var(--shadow-pop)", display: "flex", alignItems: "center", gap: 10, animation: "fade-up .25s ease" }}>
      <span className={"dot " + msg.tone} /><span style={{ fontSize: 13.5, color: "var(--text-1)" }}>{msg.text}</span>
    </div>
  );
}

/* ---------- 메인 앱 ---------- */
function App() {
  const [authed, setAuthed] = useState(false);
  const [route, setRoute] = useState("dashboard");
  const [layout, setLayout] = useState("A");
  const [feed, setFeed] = useState(() => S.FEED.slice());
  const [selected, setSelected] = useState(null);
  const [job, setJob] = useState(null);
  const [newIds, setNewIds] = useState(() => new Set());
  const [toast, setToast] = useState(null);
  const [live, setLive] = useState(true);
  const toastTimer = useRef(null);

  function showToast(text, tone = "ok") {
    setToast({ text, tone });
    clearTimeout(toastTimer.current);
    toastTimer.current = setTimeout(() => setToast(null), 2600);
  }

  // 라이브 시뮬레이션: 새 메일 인입 → 파이프라인 단계 진행 → 피드 안착
  useEffect(() => {
    if (!authed || !live) { setJob(null); return; }
    let cancelled = false;
    let stageTimer, gapTimer;
    function runOnce() {
      const email = S.makeEmail(0);
      let stage = 0;
      setJob({ email, stage });
      stageTimer = setInterval(() => {
        stage += 1;
        if (cancelled) return;
        if (stage >= STAGES.length) {
          clearInterval(stageTimer);
          setJob(null);
          setFeed((f) => [email, ...f].slice(0, 80));
          setNewIds((s) => { const n = new Set(s); n.add(email.id); return n; });
          setTimeout(() => setNewIds((s) => { const n = new Set(s); n.delete(email.id); return n; }), 4000);
          if (email.status === "quarantined") showToast(`위험 메일 자동 격리: ${email.subject.slice(0, 22)}…`, "danger");
          gapTimer = setTimeout(runOnce, 4500 + Math.random() * 4000);
        } else {
          setJob({ email, stage });
        }
      }, 620);
    }
    gapTimer = setTimeout(runOnce, 2600);
    return () => { cancelled = true; clearInterval(stageTimer); clearTimeout(gapTimer); };
  }, [authed, live]);

  function handleAction(e, action) {
    const map = { quarantine: ["quarantined", "격리 처리됨 — Quarantine label 적용", "danger"], review: ["review", "검토 큐에 등록됨 — Needs-Review label", "warn"], ok: ["normal", "정상 처리됨 — INBOX 유지", "ok"], release: ["normal", "격리 해제됨 — INBOX 복원", "ok"] };
    const [status, text, tone] = map[action];
    setFeed((f) => f.map((x) => x.id === e.id ? { ...x, status } : x));
    setSelected((s) => s ? { ...s, status } : s);
    showToast(text, tone);
  }

  const k = useMemo(() => {
    const total = feed.length;
    const q = feed.filter((e) => e.status === "quarantined").length;
    const r = feed.filter((e) => e.status === "review").length;
    const n = total - q - r;
    const avgLat = (feed.reduce((s, e) => s + e.latency, 0) / total).toFixed(1);
    return { total, q, r, n, avgLat, fpr: 1.8, fnr: 0.9, throughput: 142 };
  }, [feed]);

  if (!authed) return <LoginScreen onLogin={() => setAuthed(true)} />;

  const [title, sub] = ROUTE_TITLE[route];
  return (
    <div style={{ display: "flex", height: "100%", background: "var(--bg-1)" }}>
      <Sidebar route={route} setRoute={setRoute} onLogout={() => { setAuthed(false); setRoute("dashboard"); }} />
      <div style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0 }}>
        {/* 톱바 */}
        <header style={{ height: 64, flex: "none", borderBottom: "1px solid var(--line-soft)", display: "flex", alignItems: "center", padding: "0 24px", gap: 16, background: "var(--bg-1)" }}>
          <div style={{ minWidth: 0 }}>
            <h2 style={{ fontSize: 17, lineHeight: 1.2 }}>{title}</h2>
            <div style={{ fontSize: 12, color: "var(--text-3)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{sub}</div>
          </div>
          <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 12 }}>
            {route === "dashboard" && <LayoutSwitch layout={layout} setLayout={setLayout} />}
            <button className="btn sm" onClick={() => setLive((v) => !v)} style={{ gap: 7 }}>
              <span className="live-dot" style={{ background: live ? "var(--ok)" : "var(--text-4)", animation: live ? "blink 1.4s infinite" : "none" }} />{live ? "라이브 ON" : "일시정지"}
            </button>
            <div style={{ width: 1, height: 24, background: "var(--line)" }} />
            <button className="btn ghost sm" style={{ padding: 8, width: 34, height: 34, position: "relative" }} title="알림">
              <Icon name="bell" size={17} />
              <span style={{ position: "absolute", top: 6, right: 6, width: 7, height: 7, borderRadius: "50%", background: "var(--danger)", border: "1.5px solid var(--bg-1)" }} />
            </button>
          </div>
        </header>
        {/* 본문 */}
        <main style={{ flex: 1, padding: 24, minHeight: 0, overflow: route === "dashboard" ? "hidden" : "auto" }}>
          {route === "dashboard" && <Dashboard layout={layout} feed={feed} onSelect={setSelected} newIds={newIds} job={job} k={k} />}
          {route === "list" && <MailListScreen feed={feed} onSelect={setSelected} />}
          {route === "logs" && <LogsScreen feed={feed} onSelect={setSelected} />}
          {route === "stats" && <StatsScreen k={k} />}
        </main>
      </div>
      {selected && <DetailDrawer email={selected} onClose={() => setSelected(null)} onAction={handleAction} />}
      <Toast msg={toast} />
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
