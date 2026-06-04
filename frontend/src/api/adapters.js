export const STATUS_META = {
  quarantined: { label: "격리됨", short: "위험", tone: "danger" },
  needs_review: { label: "검토 필요", short: "의심", tone: "warn" },
  normal: { label: "정상", short: "정상", tone: "ok" },
  pending: { label: "대기", short: "대기", tone: "warn" }
};

export function statusTone(status) {
  return STATUS_META[status]?.tone || "warn";
}

export function riskColor(score) {
  if ((score || 0) >= 0.7) return "var(--danger)";
  if ((score || 0) >= 0.4) return "var(--warn)";
  return "var(--ok)";
}

export function adaptStats(raw) {
  const review = raw.suspicious || 0;
  const total = raw.total || 0;
  const quarantined = raw.quarantined || 0;
  const normal = raw.normal || 0;
  const avgSeconds = raw.avg_analysis_ms ? raw.avg_analysis_ms / 1000 : 0;
  return {
    total,
    quarantined,
    review,
    normal,
    dangerous: raw.dangerous || 0,
    avgSeconds,
    lastUpdated: raw.last_updated
  };
}

export function adaptEmailSummary(raw) {
  return {
    id: raw.id,
    messageId: raw.message_id,
    sender: raw.sender || "unknown",
    senderName: senderName(raw.sender),
    subject: raw.subject || "(제목 없음)",
    nlpScore: null,
    urlScore: null,
    ruleScore: null,
    finalScore: raw.final_score || 0,
    riskLevel: raw.risk_level || "normal",
    status: normalizeStatus(raw.status, raw.risk_level),
    receivedAt: raw.received_at || raw.created_at,
    createdAt: raw.created_at,
    urls: []
  };
}

export function adaptEmailDetail(raw) {
  const modelDetails = raw.model_details || {};
  const urlDetails = modelDetails.url_details || [];
  const urls = raw.urls_found || [];
  return {
    ...adaptEmailSummary(raw),
    senderDomain: raw.sender_domain || "",
    body: raw.body_preview || "",
    urls,
    nlpScore: raw.nlp_score || 0,
    urlScore: raw.url_score || 0,
    ruleScore: raw.rule_score || 0,
    finalScore: raw.final_score || 0,
    actionTaken: raw.action_taken || "",
    analysisMs: raw.analysis_time_ms || 0,
    keywords: modelDetails.nlp_top_features || [],
    urlDetails,
    urlFeatures: toUrlFeatures(urlDetails),
    ruleDetails: modelDetails.rule_details || {},
    receivedAt: raw.received_at || raw.created_at,
    updatedAt: raw.updated_at
  };
}

function normalizeStatus(status, riskLevel) {
  if (status === "review") return "needs_review";
  if (status && STATUS_META[status]) return status;
  if (riskLevel === "dangerous") return "quarantined";
  if (riskLevel === "suspicious") return "needs_review";
  return "normal";
}

function senderName(sender = "") {
  const clean = sender.replace(/<.*?>/g, "").trim();
  if (!clean) return "Unknown";
  if (clean.includes("@")) return clean.split("@")[0];
  return clean;
}

function toUrlFeatures(urlDetails) {
  if (!urlDetails.length) return [];
  const first = urlDetails[0] || {};
  const rows = [
    ["score", "URL 모델 점수", first.score, ""],
    ["is_https", "HTTPS 사용", first.is_https, ""],
    ["is_ip", "IP 직접 사용", first.is_ip, ""],
    ["url", "분석 URL", first.url || "", ""]
  ];
  return rows.map(([key, label, value, unit]) => ({
    key,
    label,
    value,
    unit,
    bool: typeof value === "boolean",
    good: key === "is_https",
    contrib: key === "score" ? (Number(value) || 0) - 0.5 : value ? 0.08 : -0.03
  }));
}

export function formatDateTime(value) {
  if (!value) return "-";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return "-";
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

export function formatTime(value) {
  if (!value) return "-";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return "-";
  const pad = (n) => String(n).padStart(2, "0");
  return `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
}
