/* ============================================================
   SOC 대시보드 — 화면: 로그인 / 대시보드(A·B·C) / 피드 / 목록
   ============================================================ */

/* ---------- 도넛 차트 ---------- */
function Donut({ q, r, n, size = 150 }) {
  const total = q + r + n || 1;
  const stroke = 18, rad = (size - stroke) / 2, c = 2 * Math.PI * rad;
  const segs = [
    { v: q, color: "var(--danger)", label: "위험" },
    { v: r, color: "var(--warn)", label: "의심" },
    { v: n, color: "#2a3a5e", label: "정상" },
  ];
  let off = 0;
  return (
    <div style={{ position: "relative", width: size, height: size }}>
      <svg width={size} height={size} style={{ transform: "rotate(-90deg)" }}>
        {segs.map((s, i) => {
          const frac = s.v / total, dash = c * frac;
          const el = <circle key={i} cx={size / 2} cy={size / 2} r={rad} fill="none" stroke={s.color} strokeWidth={stroke} strokeDasharray={`${dash} ${c - dash}`} strokeDashoffset={-off} style={{ transition: "stroke-dashoffset .8s" }} />;
          off += dash; return el;
        })}
      </svg>
      <div style={{ position: "absolute", inset: 0, display: "grid", placeItems: "center" }}>
        <div style={{ textAlign: "center" }}>
          <div className="mono" style={{ fontSize: 28, fontWeight: 700, color: "var(--text-1)" }}>{total}</div>
          <div style={{ fontSize: 11, color: "var(--text-3)" }}>분석 메일</div>
        </div>
      </div>
    </div>
  );
}

/* ---------- 피드 테이블 행 ---------- */
// compact=true: 대시보드용 (URL 텍스트 컬럼 생략) / false: 목록용 (전체)
const FEED_COLS_FULL = "38px minmax(0,2.4fr) minmax(0,1.5fr) 50px 50px 104px 84px";
const FEED_COLS_COMPACT = "28px minmax(0,1fr) 38px 38px 56px";
function FeedRow({ e, onSelect, isNew, compact }) {
  return (
    <div onClick={() => onSelect(e)}
      style={{ display: "grid", gridTemplateColumns: compact ? FEED_COLS_COMPACT : FEED_COLS_FULL, gap: compact ? 9 : 14, alignItems: "center",
        padding: compact ? "9px 14px 9px 11px" : "11px 16px", borderRadius: 10, cursor: "pointer", borderBottom: "1px solid var(--line-soft)",
        borderLeft: compact ? `3px solid ${riskColor(e.final)}` : "3px solid transparent",
        animation: isNew ? "slide-in .5s ease" : "none", background: isNew ? "var(--accent-soft)" : "transparent", transition: "background .15s" }}
      onMouseEnter={(ev) => (ev.currentTarget.style.background = "var(--surface-2)")}
      onMouseLeave={(ev) => (ev.currentTarget.style.background = isNew ? "var(--accent-soft)" : "transparent")}>
      <SenderGlyph name={e.name} status={e.status} size={compact ? 30 : 38} />
      <div style={{ minWidth: 0 }}>
        <div style={{ fontSize: compact ? 12.5 : 13.5, fontWeight: 600, color: "var(--text-1)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{e.subject}</div>
        <div style={{ fontSize: 11.5, color: "var(--text-3)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{compact ? e.name : e.name + " · " + e.from}</div>
      </div>
      {!compact && <div className="mono" style={{ fontSize: 11.5, color: "var(--text-3)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{e.urls.length ? e.urls[0] : "URL 없음"}</div>}
      <span className="mono" style={{ fontSize: 12.5, color: e.nlp >= 0.5 ? "var(--danger)" : "var(--text-3)", textAlign: "right" }}>{e.nlp.toFixed(2)}</span>
      <span className="mono" style={{ fontSize: 12.5, color: e.url >= 0.5 ? "var(--danger)" : "var(--text-3)", textAlign: "right" }}>{e.url.toFixed(2)}</span>
      <div style={{ display: "flex", alignItems: "center", gap: 8, justifyContent: "flex-end" }}>
        {!compact && <div style={{ flex: 1, height: 6, borderRadius: 4, background: "var(--surface-2)", overflow: "hidden", maxWidth: 40 }}>
          <div style={{ width: e.final * 100 + "%", height: "100%", background: riskColor(e.final) }} />
        </div>}
        <span className="mono" style={{ fontSize: compact ? 14 : 13, fontWeight: 700, color: riskColor(e.final) }}>{e.final.toFixed(2)}</span>
      </div>
      {!compact && <div style={{ justifySelf: "end" }}><StatusBadge status={e.status} dot={false} /></div>}
    </div>
  );
}

function FeedTableHeader({ compact }) {
  const cols = compact
    ? [["", ""], ["발신자 / 제목", "left"], ["NLP", "right"], ["URL", "right"], ["최종 위험도", "right"]]
    : [["", ""], ["발신자 / 제목", "left"], ["추출 URL", "left"], ["NLP", "right"], ["URL", "right"], ["최종 위험도", "right"], ["상태", "right"]];
  return (
    <div style={{ display: "grid", gridTemplateColumns: compact ? FEED_COLS_COMPACT : FEED_COLS_FULL, gap: compact ? 9 : 14, padding: compact ? "0 14px 9px 14px" : "0 16px 10px", borderBottom: "1px solid var(--line)" }}>
      {cols.map((c, i) => <span key={i} style={{ fontSize: 10.5, fontWeight: 700, color: "var(--text-4)", textTransform: "uppercase", letterSpacing: ".04em", textAlign: c[1] === "right" ? "right" : "left", whiteSpace: "nowrap" }}>{c[0]}</span>)}
    </div>
  );
}

/* ---------- 라이브 인입 파이프라인 배너 ---------- */
const STAGES = [
  { key: "recv", label: "수신", icon: "mail" },
  { key: "parse", label: "파싱", icon: "flow" },
  { key: "nlp", label: "NLP", icon: "cpu" },
  { key: "url", label: "URL", icon: "link" },
  { key: "ens", label: "앙상블", icon: "activity" },
  { key: "act", label: "조치", icon: "shield" },
];
function PipelineBanner({ job }) {
  const e = job.email;
  return (
    <div className="card" style={{ padding: "10px 14px", borderColor: "var(--accent)", boxShadow: "0 0 0 1px var(--accent), 0 6px 22px rgba(79,140,255,.16)", animation: "fade-up .3s ease", background: "linear-gradient(180deg, rgba(79,140,255,.08), transparent)" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 9, marginBottom: 9 }}>
        <span className="live-dot" style={{ background: "var(--accent)", flex: "none" }} />
        <span style={{ fontSize: 11.5, fontWeight: 700, color: "var(--accent)", whiteSpace: "nowrap" }}>새 메일 분석 중</span>
        <span style={{ fontSize: 12, color: "var(--text-2)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis", minWidth: 0 }}>{e.subject}</span>
        <span className="mono" style={{ fontSize: 10.5, color: "var(--text-4)", marginLeft: "auto", whiteSpace: "nowrap" }}>{e.id}</span>
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
        {STAGES.map((st, i) => {
          const done = i < job.stage, active = i === job.stage;
          const color = done ? "var(--ok)" : active ? "var(--accent)" : "var(--text-4)";
          return (
            <React.Fragment key={st.key}>
              <div style={{ display: "flex", alignItems: "center", gap: 6, flex: "none" }}>
                <div style={{ width: 22, height: 22, borderRadius: 7, display: "grid", placeItems: "center",
                  background: active ? "var(--accent-soft)" : done ? "var(--ok-bg)" : "var(--surface-2)",
                  border: `1px solid ${active ? "var(--accent)" : done ? "var(--ok-line)" : "var(--line)"}`,
                  color, animation: active ? "pulse-ring 1.2s infinite" : "none" }}>
                  {done ? <Icon name="check" size={12} /> : <Icon name={st.icon} size={12} />}
                </div>
                <span style={{ fontSize: 11, fontWeight: 600, color, whiteSpace: "nowrap" }}>{st.label}</span>
              </div>
              {i < STAGES.length - 1 && <div style={{ flex: 1, height: 2, borderRadius: 2, minWidth: 6, background: done ? "var(--ok)" : "var(--line)" }} />}
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
}

/* ---------- 로그인 화면 ---------- */
function LoginScreen({ onLogin }) {
  const [loading, setLoading] = useState(false);
  function go() { setLoading(true); setTimeout(onLogin, 1500); }
  return (
    <div style={{ height: "100%", display: "grid", gridTemplateColumns: "1.05fr .95fr", background: "var(--bg-0)" }}>
      {/* 좌: 브랜드 */}
      <div style={{ position: "relative", overflow: "hidden", padding: "56px 60px", display: "flex", flexDirection: "column", justifyContent: "space-between", background: "radial-gradient(900px 600px at 15% 0%, #14224a 0%, #0a1226 55%, #070b16 100%)" }}>
        <div style={{ position: "absolute", inset: 0, opacity: .5, backgroundImage: "linear-gradient(var(--line-soft) 1px, transparent 1px), linear-gradient(90deg, var(--line-soft) 1px, transparent 1px)", backgroundSize: "44px 44px", maskImage: "radial-gradient(circle at 30% 30%, #000, transparent 75%)" }} />
        <div style={{ position: "relative", display: "flex", alignItems: "center", gap: 12 }}>
          <Logo size={38} />
          <div>
            <div style={{ fontWeight: 800, fontSize: 18, color: "var(--text-1)", letterSpacing: "-.02em" }}>PhishGuard <span style={{ color: "var(--accent)" }}>SOC</span></div>
            <div style={{ fontSize: 12, color: "var(--text-3)" }}>피싱 메일 자동 분석·격리 시스템</div>
          </div>
        </div>
        <div style={{ position: "relative" }}>
          <h1 style={{ fontSize: 38, lineHeight: 1.18, letterSpacing: "-.03em" }}>메일이 도착하는 순간,<br/><span style={{ background: "linear-gradient(90deg,#4f8cff,#7c5cff)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>자동으로 분석하고 격리</span>합니다.</h1>
          <p style={{ fontSize: 15, color: "var(--text-2)", lineHeight: 1.7, maxWidth: 440, marginTop: 18 }}>
            Gmail API Webhook과 Ensemble AI로 본문 문맥과 URL 구조를 동시에 분석해, 사람의 개입 없이 피싱 위험도를 산출하고 SOC 대시보드에 실시간 기록합니다.
          </p>
          <div style={{ display: "flex", gap: 10, marginTop: 26, flexWrap: "wrap" }}>
            {["Gmail API + Pub/Sub", "BERT NLP", "XGBoost URL", "Ensemble Risk"].map((t) => (
              <span key={t} className="mono" style={{ fontSize: 11.5, padding: "6px 11px", borderRadius: 8, background: "rgba(255,255,255,.04)", border: "1px solid var(--line)", color: "var(--text-2)" }}>{t}</span>
            ))}
          </div>
        </div>
        <div style={{ position: "relative", fontSize: 12, color: "var(--text-4)" }}>event-driven security automation · 2026</div>
      </div>
      {/* 우: 로그인 카드 */}
      <div style={{ display: "grid", placeItems: "center", padding: 40 }}>
        <div style={{ width: "100%", maxWidth: 380 }}>
          <h2 style={{ fontSize: 24, marginBottom: 8 }}>SOC 대시보드 로그인</h2>
          <p style={{ fontSize: 14, color: "var(--text-3)", marginBottom: 30, lineHeight: 1.6 }}>모니터링 대상 Gmail 계정으로 인증합니다. 로그인 시 Gmail watch가 자동 등록되고 JWT 세션이 발급됩니다.</p>
          <button className="btn" onClick={go} disabled={loading} style={{ width: "100%", height: 50, fontSize: 15, background: "#fff", color: "#1f1f1f", border: "none", boxShadow: "0 4px 16px rgba(0,0,0,.3)" }}>
            {loading ? <><span style={{ width: 18, height: 18, border: "2px solid #ccc", borderTopColor: "#1f1f1f", borderRadius: "50%", animation: "spin .7s linear infinite", display: "inline-block" }} />Gmail watch 등록 중…</> : <><Icon name="google" size={20} stroke="none" />Google 계정으로 로그인</>}
          </button>
          <div style={{ marginTop: 22, padding: 16, borderRadius: 12, background: "var(--surface-1)", border: "1px solid var(--line-soft)" }}>
            <div style={{ fontSize: 12, fontWeight: 700, color: "var(--text-2)", marginBottom: 12 }}>로그인 시 자동 수행</div>
            {[["db", "Gmail OAuth 토큰 저장"], ["bell", "Gmail watch → Pub/Sub 연결"], ["shield", "JWT Access(15분)+Refresh(7일) 발급"]].map(([ic, t]) => (
              <div key={t} style={{ display: "flex", alignItems: "center", gap: 10, padding: "5px 0", fontSize: 13, color: "var(--text-2)" }}>
                <Icon name={ic} size={15} style={{ color: "var(--accent)" }} />{t}
              </div>
            ))}
          </div>
          <p style={{ fontSize: 11.5, color: "var(--text-4)", marginTop: 18, lineHeight: 1.6, textAlign: "center" }}>데모 계정 전용 · 실제 메일은 격리만 수행하며 삭제하지 않습니다.</p>
        </div>
      </div>
    </div>
  );
}

/* ---------- 라이브 피드 패널 (공통) ---------- */
function LiveFeedPanel({ feed, onSelect, newIds, job, title = "실시간 탐지 현황", compact = true }) {
  return (
    <div className="card" style={{ display: "flex", flexDirection: "column", overflow: "hidden", minHeight: 0 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 9, padding: "15px 16px 13px" }}>
        <span className="live-dot" style={{ flex: "none" }} /><h3 style={{ fontSize: 14.5, whiteSpace: "nowrap" }}>{title}</h3>
        <span style={{ marginLeft: "auto", fontSize: 12, color: "var(--text-3)", whiteSpace: "nowrap" }}>최근 {feed.length}건</span>
      </div>
      {job && <div style={{ padding: "0 16px 13px" }}><PipelineBanner job={job} /></div>}
      <div style={{ padding: "0 2px" }}><FeedTableHeader compact={compact} /></div>
      <div style={{ overflowY: "auto", flex: 1, padding: "6px 2px 8px" }}>
        {feed.map((e) => <FeedRow key={e.id} e={e} onSelect={onSelect} isNew={newIds && newIds.has(e.id)} compact={compact} />)}
      </div>
    </div>
  );
}

/* ---------- 모델/시스템 상태 미니 카드 ---------- */
function SystemHealth() {
  const items = [
    { label: "Gmail watch", val: "활성", sub: "22h 후 갱신", tone: "ok" },
    { label: "Pub/Sub 구독", val: "연결됨", sub: "gmail-alert-topic", tone: "ok" },
    { label: "BERT NLP", val: "로드됨", sub: "v1 · 38ms", tone: "ok" },
    { label: "XGBoost URL", val: "로드됨", sub: "16 feature", tone: "ok" },
  ];
  return (
    <div className="card" style={{ padding: "16px 18px" }}>
      <h3 style={{ fontSize: 14, marginBottom: 14 }}>시스템 상태</h3>
      <div style={{ display: "flex", flexDirection: "column", gap: 11 }}>
        {items.map((it) => (
          <div key={it.label} style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <span className="dot ok" />
            <span style={{ fontSize: 13, color: "var(--text-2)", flex: 1 }}>{it.label}</span>
            <span style={{ fontSize: 12.5, fontWeight: 600, color: "var(--ok)" }}>{it.val}</span>
            <span className="mono" style={{ fontSize: 11, color: "var(--text-4)", width: 96, textAlign: "right" }}>{it.sub}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ---------- 위험 분포 패널 ---------- */
function DistributionPanel({ k }) {
  const rows = [["danger", "위험 · 격리", k.q], ["warn", "의심 · 검토", k.r], ["ok", "정상 · 통과", k.n]];
  return (
    <div className="card" style={{ padding: "16px 18px" }}>
      <h3 style={{ fontSize: 14, marginBottom: 16 }}>위험도 분포</h3>
      <div style={{ display: "flex", alignItems: "center", gap: 18 }}>
        <Donut q={k.q} r={k.r} n={k.n} size={132} />
        <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 12 }}>
          {rows.map(([tone, label, v]) => (
            <div key={label} style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <span className={"dot " + tone} />
              <span style={{ fontSize: 13, color: "var(--text-2)", flex: 1 }}>{label}</span>
              <span className="mono" style={{ fontSize: 15, fontWeight: 700, color: "var(--text-1)" }}>{v}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

/* ========== 대시보드 레이아웃 ========== */
function Dashboard({ layout, feed, onSelect, newIds, job, k }) {
  const kpis = [
    { icon: "mail", label: "분석 메일", value: k.total, sub: "건", tone: "accent", accent: true },
    { icon: "quarantine", label: "자동 격리", value: k.q, sub: "위험", tone: "danger", accent: true },
    { icon: "eye", label: "검토 대기", value: k.r, sub: "의심", tone: "warn", accent: true },
    { icon: "clock", label: "평균 처리", value: k.avgLat, sub: "초", tone: "ok", accent: true },
  ];

  /* ---- A: 클래식 ---- */
  if (layout === "A") {
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: 16, height: "100%", minHeight: 0 }}>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 14 }}>{kpis.map((p) => <KpiCard key={p.label} {...p} />)}</div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 320px", gap: 16, flex: 1, minHeight: 0 }}>
          <LiveFeedPanel feed={feed} onSelect={onSelect} newIds={newIds} job={job} />
          <div style={{ display: "flex", flexDirection: "column", gap: 16, overflowY: "auto" }}>
            <DistributionPanel k={k} />
            <SystemHealth />
          </div>
        </div>
      </div>
    );
  }

  /* ---- B: 라이브 오퍼레이션 (피드가 주인공 — 좌측 대형 피드 + 우측 스태트 레일) ---- */
  if (layout === "B") {
    const statRows = [
      { icon: "mail", label: "분석 메일", value: k.total + "건", tone: "accent" },
      { icon: "quarantine", label: "자동 격리", value: k.q + "건", tone: "danger" },
      { icon: "eye", label: "검토 대기", value: k.r + "건", tone: "warn" },
      { icon: "clock", label: "평균 처리", value: k.avgLat + "초", tone: "ok" },
    ];
    return (
      <div style={{ display: "grid", gridTemplateColumns: "1fr 282px", gap: 16, height: "100%", minHeight: 0 }}>
        <LiveFeedPanel feed={feed} onSelect={onSelect} newIds={newIds} job={job} title="라이브 분석 피드" />
        <div style={{ display: "flex", flexDirection: "column", gap: 14, overflowY: "auto" }}>
          <div className="card" style={{ padding: "6px 4px" }}>
            {statRows.map((s, i) => {
              const color = { danger: "var(--danger)", warn: "var(--warn)", ok: "var(--ok)", accent: "var(--accent)" }[s.tone];
              return (
                <div key={s.label} style={{ display: "flex", alignItems: "center", gap: 12, padding: "11px 14px", borderBottom: i < 3 ? "1px solid var(--line-soft)" : "none" }}>
                  <div style={{ width: 30, height: 30, borderRadius: 8, background: "var(--surface-2)", display: "grid", placeItems: "center", color, flex: "none" }}><Icon name={s.icon} size={16} /></div>
                  <span style={{ fontSize: 13, color: "var(--text-2)", flex: 1 }}>{s.label}</span>
                  <span className="mono" style={{ fontSize: 18, fontWeight: 700, color: "var(--text-1)" }}>{s.value}</span>
                </div>
              );
            })}
          </div>
          <DistributionPanel k={k} />
          <SystemHealth />
        </div>
      </div>
    );
  }

  /* ---- C: 벤토 그리드 ---- */
  const latest = feed.find((e) => e.status === "quarantined") || feed[0];
  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 14, height: "100%", minHeight: 0, gridTemplateRows: "auto 1.5fr 1fr" }}>
      {kpis.map((p) => <KpiCard key={p.label} {...p} />)}
      {/* 큰 피드 */}
      <div style={{ gridColumn: "1 / 3", gridRow: "2 / 4", minHeight: 0 }}><LiveFeedPanel feed={feed} onSelect={onSelect} newIds={newIds} job={job} /></div>
      {/* 분포 (2컬럼) */}
      <div style={{ gridColumn: "3 / 5", gridRow: "2 / 3", minHeight: 0 }}><DistributionPanel k={k} /></div>
      {/* 최신 고위험 게이지 */}
      <div className="card" style={{ gridColumn: "3 / 4", gridRow: "3 / 4", padding: 16, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 10, minHeight: 0 }}>
        <h3 style={{ fontSize: 12.5, alignSelf: "flex-start", whiteSpace: "nowrap" }}>최신 고위험</h3>
        <RiskGauge score={latest.final} size={104} label="위험도" />
        <button className="btn sm" onClick={() => onSelect(latest)} style={{ width: "100%" }}>상세 <Icon name="arrow" size={13} /></button>
      </div>
      {/* 시간별 막대 */}
      <div className="card" style={{ gridColumn: "4 / 5", gridRow: "3 / 4", padding: 16, minHeight: 0, display: "flex", flexDirection: "column" }}>
        <div style={{ display: "flex", alignItems: "center", marginBottom: 12 }}><h3 style={{ fontSize: 12.5, whiteSpace: "nowrap" }}>시간대별 탐지량</h3></div>
        <div style={{ flex: 1, display: "flex", alignItems: "flex-end", minHeight: 70 }}><HourBars data={S.HOURLY} height={88} /></div>
      </div>
    </div>
  );
}

Object.assign(window, { LoginScreen, Dashboard, LiveFeedPanel, PipelineBanner, Donut, FeedRow, FeedTableHeader, SystemHealth, DistributionPanel, STAGES });
