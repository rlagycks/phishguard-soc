import { useEffect, useState } from "react";
import { formatDateTime, riskColor, STATUS_META } from "../api/adapters.js";
import { fetchEmailDetail, updateEmailStatus } from "../api/client.js";
import { Icon } from "./Icon.jsx";
import { RiskGauge } from "./RiskGauge.jsx";
import { ScoreBar } from "./ScoreBar.jsx";
import { StatusBadge } from "./StatusBadge.jsx";

const TABS = [
  ["score", "모델별 점수"],
  ["basis", "판단 근거"],
  ["url", "URL 분석"],
  ["raw", "원문"]
];

export function DetailDrawer({ emailId, onClose, onChanged }) {
  const [email, setEmail] = useState(null);
  const [tab, setTab] = useState("score");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    fetchEmailDetail(emailId)
      .then((data) => { if (!cancelled) setEmail(data); })
      .catch((err) => { if (!cancelled) setError(err.message); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [emailId]);

  async function handleStatus(status) {
    const updated = await updateEmailStatus(email.id, status);
    setEmail(updated);
    onChanged?.();
  }

  return (
    <>
      <button className="drawer-backdrop" onClick={onClose} aria-label="닫기" />
      <aside className="detail-drawer">
        <header className="drawer-head">
          {email && <div className={`sender-glyph large ${email.status}`}>{email.senderName.slice(0, 1).toUpperCase()}</div>}
          <div>
            {email && (
              <div className="drawer-meta">
                <StatusBadge status={email.status} />
                <span className="mono">{email.messageId}</span>
                <span>{formatDateTime(email.receivedAt)} · {(email.analysisMs / 1000).toFixed(1)}s 처리</span>
              </div>
            )}
            <h2>{email?.subject || "분석 상세"}</h2>
            {email && <p>{email.senderName} · <span className="mono">{email.sender}</span></p>}
          </div>
          <button className="icon-btn" onClick={onClose}><Icon name="x" size={16} /></button>
        </header>
        <nav className="drawer-tabs">
          {TABS.map(([key, label]) => (
            <button key={key} className={tab === key ? "active" : ""} onClick={() => setTab(key)}>{label}</button>
          ))}
        </nav>
        <div className="drawer-body">
          {loading && <div className="empty-state">상세 분석을 불러오는 중입니다.</div>}
          {error && <div className="error-state">{error}</div>}
          {email && tab === "score" && <ScorePanel email={email} />}
          {email && tab === "basis" && <BasisPanel email={email} />}
          {email && tab === "url" && <UrlPanel email={email} />}
          {email && tab === "raw" && <RawPanel email={email} />}
        </div>
        {email && (
          <footer className="drawer-actions">
            <span>자동 조치: <b style={{ color: riskColor(email.finalScore) }}>{STATUS_META[email.status]?.label}</b></span>
            <div>
              <button className="btn sm danger" onClick={() => handleStatus("quarantined")}><Icon name="quarantine" size={14} />수동 격리</button>
              <button className="btn sm" onClick={() => handleStatus("needs_review")}><Icon name="eye" size={14} />검토 큐</button>
              <button className="btn sm primary" onClick={() => handleStatus("normal")}><Icon name="check" size={14} />정상 처리</button>
            </div>
          </footer>
        )}
      </aside>
    </>
  );
}

function ScorePanel({ email }) {
  return (
    <div className="score-panel">
      <div className="score-grid">
        <RiskGauge score={email.finalScore} size={142} />
        <div className="score-bars">
          <ScoreBar label="이메일 본문 (NLP)" value={email.nlpScore} weight="0.45" />
          <ScoreBar label="URL 구조 (ML)" value={email.urlScore} weight="0.45" />
          <ScoreBar label="룰 기반 (Header)" value={email.ruleScore} weight="0.10" />
        </div>
      </div>
      <section className="card formula-card">
        <strong>Ensemble Risk 산출식</strong>
        <p className="mono">
          Final = 0.45*{email.nlpScore.toFixed(2)} + 0.45*{email.urlScore.toFixed(2)} + 0.10*{email.ruleScore.toFixed(2)} = <b style={{ color: riskColor(email.finalScore) }}>{email.finalScore.toFixed(2)}</b>
        </p>
        <small>임계값: 0.40 미만 정상 · 0.40-0.69 검토 · 0.70 이상 격리</small>
      </section>
    </div>
  );
}

function BasisPanel({ email }) {
  return (
    <div className="section-stack">
      <section>
        <h3><Icon name="cpu" size={16} />위험 키워드 (NLP)</h3>
        <div className="keyword-row">
          {email.keywords.length ? email.keywords.map((kw) => <span className="badge danger" key={kw}>{kw}</span>) : <span className="empty-inline">탐지된 위험 키워드 없음</span>}
        </div>
      </section>
      <section>
        <h3><Icon name="alert" size={16} />헤더 / 룰 기반 분석</h3>
        <CheckRow label="Rule 점수" value={email.ruleScore.toFixed(2)} ok={email.ruleScore < 0.4} />
        <CheckRow label="조치 결과" value={email.actionTaken || "-"} ok={email.status === "normal"} />
      </section>
    </div>
  );
}

function UrlPanel({ email }) {
  return (
    <div className="section-stack">
      <section>
        <h3><Icon name="link" size={16} />추출된 URL</h3>
        {email.urls.length ? email.urls.map((url) => <p className="url-line mono" key={url}>{url}</p>) : <span className="empty-inline">본문에 포함된 URL 없음</span>}
      </section>
      <section>
        <h3><Icon name="chart" size={16} />URL 분석 결과</h3>
        {email.urlDetails.length ? email.urlDetails.map((detail, index) => (
          <div className="url-detail" key={`${detail.url}-${index}`}>
            <span className="mono">{detail.url}</span>
            <b style={{ color: riskColor(detail.score || 0) }}>{Number(detail.score || 0).toFixed(2)}</b>
          </div>
        )) : <span className="empty-inline">URL 모델 상세 결과 없음</span>}
      </section>
    </div>
  );
}

function RawPanel({ email }) {
  return (
    <section className="card raw-card">
      <small>제목</small>
      <strong>{email.subject}</strong>
      <small>본문 미리보기</small>
      <pre>{email.body || "본문 미리보기가 없습니다."}</pre>
    </section>
  );
}

function CheckRow({ ok, label, value }) {
  return (
    <div className="check-row">
      <span className={`dot ${ok ? "ok" : "danger"}`} />
      <span>{label}</span>
      <b>{value}</b>
    </div>
  );
}
