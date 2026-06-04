import { formatDateTime, riskColor } from "../api/adapters.js";
import { StatusBadge } from "./StatusBadge.jsx";

export function EmailTable({ emails, onSelect, compact = false }) {
  return (
    <div className={`email-table ${compact ? "compact" : ""}`}>
      <div className="email-head">
        <span />
        <span>발신자 / 제목</span>
        {!compact && <span>수신 시각</span>}
        <span>NLP</span>
        <span>URL</span>
        <span>최종 위험도</span>
        {!compact && <span>상태</span>}
      </div>
      <div className="email-body">
        {emails.length === 0 ? (
          <div className="empty-state">조건에 맞는 메일이 없습니다.</div>
        ) : (
          emails.map((email) => <EmailRow key={email.id} email={email} onSelect={onSelect} compact={compact} />)
        )}
      </div>
    </div>
  );
}

function EmailRow({ email, onSelect, compact }) {
  const score = email.finalScore || 0;
  return (
    <button className="email-row" onClick={() => onSelect(email.id)} style={{ borderLeftColor: riskColor(score) }}>
      <div className={`sender-glyph ${email.status}`}>{email.senderName.slice(0, 1).toUpperCase()}</div>
      <div className="email-title">
        <strong>{email.subject}</strong>
        <span>{email.senderName} · {email.sender}</span>
      </div>
      {!compact && <span className="email-muted">{formatDateTime(email.receivedAt)}</span>}
      <ScoreCell value={email.nlpScore} />
      <ScoreCell value={email.urlScore} />
      <span className="final-score mono" style={{ color: riskColor(score) }}>{score.toFixed(2)}</span>
      {!compact && <StatusBadge status={email.status} dot={false} />}
    </button>
  );
}

function ScoreCell({ value }) {
  if (value === null || value === undefined) return <span className="email-muted mono">-</span>;
  return <span className="mono score-cell">{value.toFixed(2)}</span>;
}
