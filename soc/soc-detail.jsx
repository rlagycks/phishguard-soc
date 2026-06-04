/* ============================================================
   SOC 대시보드 — 상세 분석 드로어 / 위험 메일 목록 / 로그 / 통계
   ============================================================ */

/* ---------- URL feature 기여도 막대 (SHAP 스타일) ---------- */
function FeatureContribRow({ f }) {
  const pos = f.contrib >= 0;
  const w = Math.min(Math.abs(f.contrib) * 320, 100);
  let display;
  if (f.bool) display = f.value ? "예" : "아니오";
  else display = f.value + (f.unit ? f.unit : "");
  return (
    <div style={{ display: "grid", gridTemplateColumns: "150px 70px 1fr", gap: 10, alignItems: "center", padding: "5px 0" }}>
      <span style={{ fontSize: 12.5, color: "var(--text-2)" }}>{f.label}</span>
      <span className="mono" style={{ fontSize: 12.5, fontWeight: 600, color: f.bool ? (f.value ? (f.good ? "var(--ok)" : "var(--danger)") : "var(--text-3)") : "var(--text-1)", textAlign: "right" }}>{display}</span>
      <div style={{ position: "relative", height: 14, display: "flex", alignItems: "center" }}>
        <div style={{ position: "absolute", left: "50%", top: 0, bottom: 0, width: 1, background: "var(--line)" }} />
        <div style={{ position: "absolute", left: pos ? "50%" : `calc(50% - ${w / 2}%)`, width: w / 2 + "%", height: 8, borderRadius: 3, background: pos ? "var(--danger)" : "var(--ok)", opacity: .85 }} />
      </div>
    </div>
  );
}

/* ---------- 상세 분석 드로어 ---------- */
function DetailDrawer({ email, onClose, onAction }) {
  const e = email;
  const [tab, setTab] = useState("score");
  const [open, setOpen] = useState(false);
  useEffect(() => { const t = requestAnimationFrame(() => setOpen(true)); return () => cancelAnimationFrame(t); }, []);
  if (!e) return null;
  const topFeatures = [...e.urlFeatures].sort((a, b) => Math.abs(b.contrib) - Math.abs(a.contrib)).slice(0, 8);
  return (
    <>
      <div onClick={onClose} style={{ position: "fixed", inset: 0, background: "rgba(4,8,16,.6)", zIndex: 40, opacity: open ? 1 : 0, transition: "opacity .25s ease", backdropFilter: "blur(2px)" }} />
      <div style={{ position: "fixed", top: 0, right: 0, bottom: 0, width: 620, maxWidth: "92vw", background: "var(--bg-1)", borderLeft: "1px solid var(--line)", zIndex: 41, boxShadow: "var(--shadow-pop)", display: "flex", flexDirection: "column", transform: open ? "translateX(0)" : "translateX(40px)", opacity: open ? 1 : 0, transition: "transform .3s cubic-bezier(.2,.7,.2,1), opacity .3s ease" }}>
        {/* 헤더 */}
        <div style={{ padding: "18px 22px", borderBottom: "1px solid var(--line)", display: "flex", alignItems: "flex-start", gap: 14 }}>
          <SenderGlyph name={e.name} status={e.status} size={44} />
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 5 }}>
              <StatusBadge status={e.status} />
              <span className="mono" style={{ fontSize: 11.5, color: "var(--text-4)" }}>{e.id}</span>
              <span style={{ fontSize: 11.5, color: "var(--text-4)" }}>· {S.fmtDateTime(e.ts)} · {e.latency}s 처리</span>
            </div>
            <h3 style={{ fontSize: 17, lineHeight: 1.3 }}>{e.subject}</h3>
            <div style={{ fontSize: 13, color: "var(--text-3)", marginTop: 4 }}>{e.name} · <span className="mono">{e.from}</span></div>
          </div>
          <button className="btn ghost sm" onClick={onClose} style={{ flex: "none", padding: 8, width: 32, height: 32 }}><Icon name="x" size={16} /></button>
        </div>

        {/* 탭 */}
        <div style={{ display: "flex", gap: 4, padding: "10px 22px 0", borderBottom: "1px solid var(--line)" }}>
          {[["score", "모델별 점수"], ["basis", "판단 근거"], ["url", "URL 분석"], ["raw", "원문"]].map(([key, label]) => (
            <button key={key} onClick={() => setTab(key)} style={{ background: "none", border: "none", padding: "10px 12px", fontSize: 13.5, fontWeight: 600, whiteSpace: "nowrap", color: tab === key ? "var(--text-1)" : "var(--text-3)", borderBottom: `2px solid ${tab === key ? "var(--accent)" : "transparent"}`, marginBottom: -1 }}>{label}</button>
          ))}
        </div>

        {/* 본문 */}
        <div style={{ flex: 1, overflowY: "auto", padding: 22 }}>
          {tab === "score" && (
            <div style={{ display: "flex", flexDirection: "column", gap: 22 }}>
              <div style={{ display: "flex", gap: 24, alignItems: "center" }}>
                <RiskGauge score={e.final} size={140} />
                <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 16 }}>
                  <ScoreBar label="이메일 본문 (NLP)" value={e.nlp} weight="0.45" delay={100} />
                  <ScoreBar label="URL 구조 (ML)" value={e.url} weight="0.45" delay={250} />
                  <ScoreBar label="룰 기반 (Header)" value={e.rule} weight="0.10" delay={400} />
                </div>
              </div>
              <div className="card" style={{ padding: "14px 16px", background: "var(--surface-1)" }}>
                <div style={{ fontSize: 12, fontWeight: 700, color: "var(--text-3)", marginBottom: 8, textTransform: "uppercase", letterSpacing: ".03em" }}>Ensemble Risk 산출식</div>
                <div className="mono" style={{ fontSize: 13, color: "var(--text-2)", lineHeight: 1.7 }}>
                  Final = 0.45×<span style={{ color: "var(--accent)" }}>{e.nlp.toFixed(2)}</span> + 0.45×<span style={{ color: "var(--accent)" }}>{e.url.toFixed(2)}</span> + 0.10×<span style={{ color: "var(--accent)" }}>{e.rule.toFixed(2)}</span> = <span style={{ color: riskColor(e.final), fontWeight: 700 }}>{e.final.toFixed(2)}</span>
                </div>
                <div style={{ marginTop: 10, fontSize: 12.5, color: "var(--text-3)" }}>임계값: 0.40 미만 정상 · 0.40–0.69 검토 · 0.70 이상 격리</div>
              </div>
            </div>
          )}

          {tab === "basis" && (
            <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
              <Section title="위험 키워드 (NLP)" icon="cpu">
                {e.keywords.length ? (
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                    {e.keywords.map((kw) => <span key={kw} className="badge danger">{kw}</span>)}
                  </div>
                ) : <Empty>본문에서 탐지된 위험 키워드 없음</Empty>}
                {e.ctx.length > 0 && <div style={{ marginTop: 12, fontSize: 12.5, color: "var(--text-3)" }}>탐지된 문맥 유형: {e.ctx.join(" · ")}</div>}
              </Section>
              <Section title="헤더 / 인증 이상" icon="alert">
                <CheckRow ok={!e.spfFail} label="SPF 인증" val={e.spfFail ? "실패 (발신 도메인 불일치)" : "통과"} />
                <CheckRow ok={!e.headerAnomaly} label="발신자 표시명 ↔ 주소" val={e.headerAnomaly ? "불일치 (사칭 의심)" : "일치"} />
                <CheckRow ok={e.attachments.length === 0} label="첨부파일" val={e.attachments.length ? e.attachments.join(", ") : "없음"} />
              </Section>
            </div>
          )}

          {tab === "url" && (
            <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
              {e.urls.length === 0 ? <Empty>본문에 포함된 URL 없음</Empty> : (
                <>
                  <Section title="추출된 URL" icon="link">
                    {e.urls.map((u, i) => (
                      <div key={i} className="mono" style={{ fontSize: 12.5, color: "var(--text-2)", padding: "8px 10px", background: "var(--surface-2)", borderRadius: 8, marginBottom: 6, wordBreak: "break-all", borderLeft: "2px solid var(--danger)" }}>{u}</div>
                    ))}
                    <div style={{ fontSize: 11.5, color: "var(--text-4)", marginTop: 4 }}>※ 정적 분석만 수행 — 실제 접속하지 않습니다.</div>
                  </Section>
                  <Section title="URL Feature 기여도 (XGBoost · SHAP)" icon="chart">
                    <div style={{ display: "grid", gridTemplateColumns: "150px 70px 1fr", gap: 10, padding: "0 0 6px", fontSize: 10.5, fontWeight: 700, color: "var(--text-4)", textTransform: "uppercase" }}>
                      <span>Feature</span><span style={{ textAlign: "right" }}>값</span>
                      <span style={{ display: "flex", justifyContent: "space-between" }}><span style={{ color: "var(--ok)" }}>← 정상</span><span style={{ color: "var(--danger)" }}>위험 →</span></span>
                    </div>
                    {topFeatures.map((f) => <FeatureContribRow key={f.key} f={f} />)}
                  </Section>
                </>
              )}
            </div>
          )}

          {tab === "raw" && (
            <div className="card" style={{ padding: 18, background: "var(--surface-1)" }}>
              <div style={{ fontSize: 12, color: "var(--text-3)", marginBottom: 4 }}>제목</div>
              <div style={{ fontSize: 14, color: "var(--text-1)", fontWeight: 600, marginBottom: 14 }}>{e.subject}</div>
              <div style={{ fontSize: 12, color: "var(--text-3)", marginBottom: 4 }}>본문 (일부)</div>
              <pre style={{ fontFamily: "var(--font)", fontSize: 13.5, color: "var(--text-2)", lineHeight: 1.75, whiteSpace: "pre-wrap", margin: 0 }}>{e.body}</pre>
            </div>
          )}
        </div>

        {/* 액션 바 */}
        <div style={{ padding: "14px 22px", borderTop: "1px solid var(--line)", display: "flex", gap: 10, alignItems: "center", background: "var(--surface-1)" }}>
          <span style={{ fontSize: 12.5, color: "var(--text-3)" }}>자동 조치: <b style={{ color: riskColor(e.final) }}>{S.STATUS_META[e.status].ko}</b></span>
          <div style={{ marginLeft: "auto", display: "flex", gap: 8 }}>
            {e.status === "quarantined"
              ? <button className="btn sm" onClick={() => onAction(e, "release")}><Icon name="refresh" size={14} />격리 해제</button>
              : <button className="btn sm danger" onClick={() => onAction(e, "quarantine")}><Icon name="quarantine" size={14} />수동 격리</button>}
            <button className="btn sm" onClick={() => onAction(e, "review")}><Icon name="eye" size={14} />검토 큐</button>
            <button className="btn sm primary" onClick={() => onAction(e, "ok")}><Icon name="check" size={14} />정상 처리</button>
          </div>
        </div>
      </div>
    </>
  );
}

function Section({ title, icon, children }) {
  return (
    <div>
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
        <Icon name={icon} size={16} style={{ color: "var(--accent)" }} />
        <h4 style={{ fontSize: 13.5 }}>{title}</h4>
      </div>
      {children}
    </div>
  );
}
function Empty({ children }) { return <div style={{ fontSize: 13, color: "var(--text-4)", padding: "10px 0" }}>{children}</div>; }
function CheckRow({ ok, label, val }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "7px 0", borderBottom: "1px solid var(--line-soft)" }}>
      <span className={"dot " + (ok ? "ok" : "danger")} />
      <span style={{ fontSize: 13, color: "var(--text-2)", flex: 1 }}>{label}</span>
      <span style={{ fontSize: 12.5, fontWeight: 600, color: ok ? "var(--ok)" : "var(--danger)" }}>{val}</span>
    </div>
  );
}

/* ---------- 위험 메일 목록 ---------- */
function MailListScreen({ feed, onSelect }) {
  const [filter, setFilter] = useState("all");
  const [sort, setSort] = useState("final");
  const [q, setQ] = useState("");
  let rows = feed.filter((e) => (filter === "all" || e.status === filter) && (q === "" || e.subject.includes(q) || e.from.includes(q)));
  rows = [...rows].sort((a, b) => sort === "final" ? b.final - a.final : new Date(b.ts) - new Date(a.ts));
  const filters = [["all", "전체", feed.length], ["quarantined", "격리", feed.filter(e => e.status === "quarantined").length], ["review", "검토", feed.filter(e => e.status === "review").length], ["normal", "정상", feed.filter(e => e.status === "normal").length]];
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16, height: "100%", minHeight: 0 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
        <div style={{ display: "flex", gap: 6, background: "var(--surface-1)", padding: 4, borderRadius: 11, border: "1px solid var(--line-soft)", flex: "none" }}>
          {filters.map(([key, label, n]) => (
            <button key={key} onClick={() => setFilter(key)} style={{ border: "none", background: filter === key ? "var(--surface-3)" : "transparent", color: filter === key ? "var(--text-1)" : "var(--text-3)", padding: "7px 13px", borderRadius: 8, fontSize: 13, fontWeight: 600, display: "flex", alignItems: "center", gap: 7, whiteSpace: "nowrap" }}>
              {label}<span className="mono" style={{ fontSize: 11.5, color: "var(--text-4)" }}>{n}</span>
            </button>
          ))}
        </div>
        <div style={{ position: "relative", flex: 1, maxWidth: 240, minWidth: 150 }}>
          <Icon name="search" size={16} style={{ position: "absolute", left: 12, top: 12, color: "var(--text-4)" }} />
          <input className="input" placeholder="제목·발신자 검색" value={q} onChange={(e) => setQ(e.target.value)} style={{ paddingLeft: 36 }} />
        </div>
        <button className="btn sm" onClick={() => setSort(sort === "final" ? "time" : "final")} style={{ marginLeft: "auto" }}>
          <Icon name="filter" size={14} />정렬: {sort === "final" ? "위험도순" : "최신순"}
        </button>
      </div>
      <div className="card" style={{ flex: 1, minHeight: 0, display: "flex", flexDirection: "column", overflow: "hidden", padding: "14px 2px 8px" }}>
        <div style={{ padding: "0 2px" }}><FeedTableHeader /></div>
        <div style={{ overflowY: "auto", flex: 1, padding: "6px 2px" }}>
          {rows.length ? rows.map((e) => <FeedRow key={e.id} e={e} onSelect={onSelect} />) : <Empty>조건에 맞는 메일이 없습니다.</Empty>}
        </div>
      </div>
    </div>
  );
}

/* ---------- 자동 대응 로그 ---------- */
function LogsScreen({ onSelect, feed }) {
  const log = S.LOG;
  return (
    <div className="card" style={{ height: "100%", minHeight: 0, display: "flex", flexDirection: "column", overflow: "hidden" }}>
      <div style={{ padding: "16px 20px", borderBottom: "1px solid var(--line)", display: "flex", alignItems: "center", gap: 10 }}>
        <Icon name="activity" size={18} style={{ color: "var(--accent)" }} />
        <h3 style={{ fontSize: 15 }}>자동 대응 로그</h3>
        <span className="badge ghost" style={{ marginLeft: 4 }}>Action Engine</span>
        <span style={{ marginLeft: "auto", fontSize: 12, color: "var(--text-3)" }}>{log.length}건 · 감사 추적용 보존</span>
      </div>
      <div style={{ overflowY: "auto", flex: 1 }}>
        {log.map((l, i) => {
          const e = feed.find((x) => x.id === l.id);
          return (
            <div key={i} onClick={() => e && onSelect(e)} style={{ display: "grid", gridTemplateColumns: "82px 28px 1fr 200px 90px", gap: 14, alignItems: "center", padding: "12px 20px", borderBottom: "1px solid var(--line-soft)", cursor: "pointer" }}
              onMouseEnter={(ev) => ev.currentTarget.style.background = "var(--surface-2)"} onMouseLeave={(ev) => ev.currentTarget.style.background = "transparent"}>
              <span className="mono" style={{ fontSize: 12, color: "var(--text-3)" }}>{S.fmtTime(l.ts)}</span>
              <span className={"dot " + l.tone} />
              <div style={{ minWidth: 0 }}>
                <div style={{ fontSize: 13, color: "var(--text-1)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{l.subject}</div>
                <div className="mono" style={{ fontSize: 11.5, color: "var(--text-4)" }}>{l.from}</div>
              </div>
              <span style={{ fontSize: 12.5, color: l.tone === "danger" ? "var(--danger)" : l.tone === "warn" ? "var(--warn)" : "var(--text-3)", fontWeight: 500 }}>{l.action}</span>
              <span className="mono" style={{ fontSize: 13, fontWeight: 700, color: riskColor(l.final), textAlign: "right" }}>{l.final.toFixed(2)}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

/* ---------- 통계 ---------- */
function StatsScreen({ k }) {
  const metrics = [
    { label: "오탐률 (FPR)", value: k.fpr + "%", desc: "정상 메일을 위험으로 격리한 비율", tone: "warn" },
    { label: "미탐률 (FNR)", value: k.fnr + "%", desc: "피싱 메일을 놓친 비율", tone: "danger" },
    { label: "처리량", value: k.throughput, desc: "분당 처리 가능 메일 수", tone: "accent" },
    { label: "평균 분석 시간", value: k.avgLat + "s", desc: "메일 1건당 E2E 처리 시간", tone: "ok" },
  ];
  const models = [
    { name: "이메일 본문 (BERT)", acc: 97.2, f1: 0.971 },
    { name: "URL (XGBoost)", acc: 95.8, f1: 0.956 },
    { name: "가중합 앙상블", acc: 98.4, f1: 0.982 },
    { name: "Stacking 앙상블", acc: 98.9, f1: 0.987 },
  ];
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16, height: "100%", overflowY: "auto", overflowX: "hidden" }}>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 14 }}>
        {metrics.map((m) => (
          <div key={m.label} className="card" style={{ padding: "18px 20px" }}>
            <div style={{ fontSize: 12.5, color: "var(--text-3)", fontWeight: 600 }}>{m.label}</div>
            <div className="mono" style={{ fontSize: 30, fontWeight: 700, color: { warn: "var(--warn)", danger: "var(--danger)", accent: "var(--accent)", ok: "var(--ok)" }[m.tone], margin: "8px 0 6px" }}>{m.value}</div>
            <div style={{ fontSize: 12, color: "var(--text-4)", lineHeight: 1.5 }}>{m.desc}</div>
          </div>
        ))}
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "1.25fr 1fr", gap: 16 }}>
        <div className="card" style={{ padding: 20 }}>
          <h3 style={{ fontSize: 15, marginBottom: 18 }}>시간대별 탐지량 <span style={{ fontSize: 12, color: "var(--text-3)", fontWeight: 400 }}>· 최근 24시간</span></h3>
          <HourBars data={S.HOURLY} height={180} />
          <div style={{ display: "flex", gap: 18, marginTop: 14 }}>
            {[["danger", "격리"], ["warn", "검토"], ["#2a3a5e", "정상"]].map(([c, l]) => (
              <span key={l} style={{ display: "flex", alignItems: "center", gap: 7, fontSize: 12.5, color: "var(--text-3)" }}><span style={{ width: 10, height: 10, borderRadius: 3, background: c.startsWith("#") ? c : `var(--${c})` }} />{l}</span>
            ))}
          </div>
        </div>
        <div className="card" style={{ padding: 20 }}>
          <h3 style={{ fontSize: 15, marginBottom: 18 }}>모델별 성능 비교</h3>
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            {models.map((m) => (
              <div key={m.name}>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6, gap: 8 }}>
                  <span style={{ fontSize: 13, color: "var(--text-2)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{m.name}</span>
                  <span className="mono" style={{ fontSize: 13, fontWeight: 700, color: "var(--text-1)", flex: "none" }}>{m.acc}%</span>
                </div>
                <div style={{ height: 7, borderRadius: 4, background: "var(--surface-2)", overflow: "hidden" }}>
                  <div style={{ width: m.acc + "%", height: "100%", background: "linear-gradient(90deg,#4f8cff,#7c5cff)" }} />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { DetailDrawer, MailListScreen, LogsScreen, StatsScreen, FeatureContribRow });
