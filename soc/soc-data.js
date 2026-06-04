/* ============================================================
   SOC 대시보드 — 가짜 데이터 생성기
   기획서 톤에 맞춘 한국어 피싱/정상 메일, 점수, URL feature, 로그
   window.SOC 네임스페이스에 노출
   ============================================================ */
(function () {
  "use strict";

  // ---- 위험도 → 상태 매핑 (기획서 6.2) -------------------------
  function statusFromScore(score) {
    if (score >= 0.7) return "quarantined";
    if (score >= 0.4) return "review";
    return "normal";
  }
  const STATUS_META = {
    quarantined: { ko: "격리됨", short: "위험", tone: "danger" },
    review: { ko: "검토 필요", short: "의심", tone: "warn" },
    normal: { ko: "정상", short: "정상", tone: "ok" },
  };

  // ---- 샘플 발신자/제목 풀 ------------------------------------
  const PHISH = [
    { from: "security-alert@account-verify.com", name: "Google 보안팀", subject: "[긴급] 비정상 로그인이 감지되었습니다", brand: "Google", ctx: ["긴급성", "계정 탈취 유도", "사칭"] },
    { from: "no-reply@paypa1-secure.net", name: "PayPal Service", subject: "결제 정보 확인이 필요합니다 — 24시간 내 처리", brand: "PayPal", ctx: ["금융 유도", "긴급성"] },
    { from: "support@kookmin-bank.help", name: "KB국민은행", subject: "[국민은행] 계좌 이용 제한 안내", brand: "KB", ctx: ["사칭", "협박성 표현"] },
    { from: "noreply@nts-refund.co", name: "국세청 홈택스", subject: "[국세청] 부가가치세 환급 신청 안내", brand: "NTS", ctx: ["금융 유도", "사칭"] },
    { from: "delivery@cj-logistics.support", name: "CJ대한통운", subject: "택배 배송 실패 — 주소를 재확인해 주세요", brand: "CJ", ctx: ["링크 클릭 유도", "사칭"] },
    { from: "admin@m1crosoft-account.com", name: "Microsoft Account", subject: "비밀번호가 곧 만료됩니다. 지금 재설정하세요", brand: "Microsoft", ctx: ["계정 탈취 유도", "긴급성"] },
    { from: "billing@netfllx-pay.com", name: "Netflix", subject: "결제 오류로 멤버십이 정지될 예정입니다", brand: "Netflix", ctx: ["금융 유도", "협박성 표현"] },
    { from: "hr-team@company-portaI.com", name: "인사팀", subject: "급여명세서 확인을 위해 로그인 인증이 필요합니다", brand: "Corp", ctx: ["계정 탈취 유도", "사칭"] },
    { from: "alert@apple-id-locked.net", name: "Apple Support", subject: "Apple ID가 잠겼습니다. 잠금 해제 안내", brand: "Apple", ctx: ["계정 탈취 유도", "협박성 표현"] },
    { from: "secure@coupang-event.shop", name: "쿠팡 이벤트", subject: "축하합니다! 100만원 상당의 경품에 당첨되셨습니다", brand: "Coupang", ctx: ["링크 클릭 유도", "금융 유도"] },
  ];
  const BENIGN = [
    { from: "newsletter@medium.com", name: "Medium Daily Digest", subject: "오늘의 추천 아티클 5선", brand: "Medium" },
    { from: "no-reply@github.com", name: "GitHub", subject: "[soc-pipeline] 새로운 pull request가 등록되었습니다", brand: "GitHub" },
    { from: "calendar@company.com", name: "사내 캘린더", subject: "내일 10:00 주간 스프린트 회의 일정 안내", brand: "Corp" },
    { from: "hr@company.com", name: "인사팀", subject: "11월 급여명세서가 발송되었습니다", brand: "Corp" },
    { from: "noreply@slack.com", name: "Slack", subject: "#general 채널의 읽지 않은 메시지 3건", brand: "Slack" },
    { from: "team@notion.so", name: "Notion", subject: "이번 주 워크스페이스 활동 요약", brand: "Notion" },
    { from: "noreply@figma.com", name: "Figma", subject: "디자인 파일에 새 코멘트가 달렸습니다", brand: "Figma" },
    { from: "research@arxiv.org", name: "arXiv", subject: "관심 분야 신규 논문 알림 (cs.CR)", brand: "arXiv" },
  ];

  const URL_SAMPLES_PHISH = [
    "http://account-verify.com/login/secure?id=8f3a&verify=1",
    "https://paypa1-secure.net/webscr/update-billing/confirm.php",
    "http://192.168.41.207/kb/auth/reset?token=eyJ0eXAi",
    "https://bit.ly/3xQz9-refund",
    "http://xn--80ak6aa92e.com/apple/unlock",
    "https://cj-logistics.support/track/redelivery?addr=re-enter",
  ];
  const URL_SAMPLES_BENIGN = [
    "https://medium.com/feed/recommended",
    "https://github.com/soc-pipeline/pulls/142",
    "https://notion.so/workspace/weekly-digest",
    "https://arxiv.org/abs/2401.04578",
  ];

  // ---- URL feature 정의 (기획서 5.2, 16 feature) ---------------
  const URL_FEATURES = [
    { key: "url_length", label: "URL 길이", unit: "자" },
    { key: "domain_length", label: "도메인 길이", unit: "자" },
    { key: "subdomain_count", label: "서브도메인 수", unit: "" },
    { key: "has_ip", label: "IP 직접 사용", bool: true },
    { key: "has_at", label: "@ 기호 포함", bool: true },
    { key: "dash_count", label: "하이픈(-) 개수", unit: "" },
    { key: "digit_ratio", label: "숫자 비율", unit: "%" },
    { key: "is_https", label: "HTTPS 사용", bool: true, good: true },
    { key: "suspicious_tld", label: "의심 TLD", bool: true },
    { key: "is_shortener", label: "URL 단축 서비스", bool: true },
    { key: "is_punycode", label: "Punycode 도메인", bool: true },
    { key: "kw_login", label: "키워드: login/verify", bool: true },
    { key: "kw_secure", label: "키워드: secure/account", bool: true },
    { key: "domain_age_days", label: "도메인 나이", unit: "일" },
    { key: "redirect_count", label: "리다이렉트 추정", unit: "" },
    { key: "entropy", label: "문자열 엔트로피", unit: "" },
  ];

  function rand(min, max) { return Math.random() * (max - min) + min; }
  function pick(arr) { return arr[Math.floor(Math.random() * arr.length)]; }
  function clamp(v, a, b) { return Math.max(a, Math.min(b, v)); }

  // SHAP-style 기여도를 가진 URL feature 값 생성
  function urlFeatureValues(isPhish) {
    return URL_FEATURES.map((f) => {
      let value, contrib;
      if (f.bool) {
        const on = isPhish ? Math.random() < 0.6 : Math.random() < 0.12;
        value = f.good ? !on : on;
        const flag = f.good ? !value : value;
        contrib = flag ? rand(0.04, 0.16) : -rand(0.01, 0.05);
      } else {
        switch (f.key) {
          case "url_length": value = Math.round(isPhish ? rand(60, 140) : rand(22, 55)); contrib = (value - 50) / 600; break;
          case "domain_length": value = Math.round(isPhish ? rand(18, 34) : rand(8, 16)); contrib = (value - 14) / 200; break;
          case "subdomain_count": value = Math.round(isPhish ? rand(2, 5) : rand(0, 1)); contrib = value * 0.03; break;
          case "digit_ratio": value = Math.round(isPhish ? rand(12, 38) : rand(0, 6)); contrib = value / 400; break;
          case "domain_age_days": value = Math.round(isPhish ? rand(2, 60) : rand(400, 4000)); contrib = value < 90 ? 0.12 : -0.06; break;
          case "redirect_count": value = Math.round(isPhish ? rand(1, 4) : 0); contrib = value * 0.03; break;
          case "entropy": value = +(isPhish ? rand(3.4, 4.6) : rand(2.1, 3.2)).toFixed(2); contrib = (value - 3) * 0.06; break;
          default: value = 0; contrib = 0;
        }
      }
      return { ...f, value, contrib: +contrib.toFixed(3) };
    });
  }

  // 위험 키워드 (NLP 설명용)
  const PHISH_KEYWORDS = ["즉시 확인", "24시간 내", "계정 정지", "비밀번호 재설정", "로그인 인증", "보안 페이지", "결제 오류", "환급", "지금 클릭", "미조치 시 차단"];

  function bodySnippet(item, isPhish) {
    if (isPhish) {
      return `안녕하세요, ${item.name}입니다.\n고객님의 계정에서 비정상적인 활동이 감지되어 즉시 확인이 필요합니다. 아래 보안 페이지에 접속하여 24시간 내에 본인 인증을 완료하지 않으면 계정이 정지될 수 있습니다.\n\n▶ 보안 페이지 바로가기`;
    }
    return `안녕하세요,\n${item.subject} 관련 안내드립니다. 자세한 내용은 아래 링크 또는 첨부 파일을 확인해 주세요. 감사합니다.`;
  }

  // 메일 1건 생성
  let SEQ = 1;
  function makeEmail(minutesAgo, forcePhish) {
    const isPhish = forcePhish != null ? forcePhish : Math.random() < 0.55;
    const item = isPhish ? pick(PHISH) : pick(BENIGN);
    const nlp = isPhish ? rand(0.55, 0.97) : rand(0.02, 0.3);
    const url = isPhish ? rand(0.45, 0.95) : rand(0.02, 0.28);
    const rule = isPhish ? rand(0.4, 0.95) : rand(0.0, 0.25);
    const final = clamp(0.45 * nlp + 0.45 * url + 0.1 * rule + rand(-0.03, 0.03), 0, 1);
    const status = statusFromScore(final);
    const urls = isPhish
      ? [pick(URL_SAMPLES_PHISH), Math.random() < 0.4 ? pick(URL_SAMPLES_PHISH) : null].filter(Boolean)
      : (Math.random() < 0.7 ? [pick(URL_SAMPLES_BENIGN)] : []);
    const ts = new Date(Date.now() - minutesAgo * 60000 - Math.floor(rand(0, 60)) * 1000);
    const kws = isPhish ? PHISH_KEYWORDS.filter(() => Math.random() < 0.5).slice(0, 4) : [];
    if (isPhish && kws.length === 0) kws.push(pick(PHISH_KEYWORDS));
    const latency = +(rand(2.4, 8.6)).toFixed(1);
    return {
      id: "MSG-" + String(10000 + SEQ++),
      isPhish,
      from: item.from,
      name: item.name,
      brand: item.brand,
      subject: item.subject,
      body: bodySnippet(item, isPhish),
      ctx: item.ctx || [],
      ts: ts.toISOString(),
      nlp: +nlp.toFixed(2),
      url: +url.toFixed(2),
      rule: +rule.toFixed(2),
      final: +final.toFixed(2),
      status,
      urls,
      urlFeatures: urls.length ? urlFeatureValues(isPhish) : [],
      keywords: kws,
      latency,
      headerAnomaly: isPhish ? Math.random() < 0.7 : false,
      spfFail: isPhish ? Math.random() < 0.6 : false,
      attachments: Math.random() < 0.2 ? [pick(["invoice_2026.pdf.html", "보안인증서.zip", "결제내역.xlsx"])] : [],
    };
  }

  function makeFeed(n) {
    const out = [];
    let t = 1;
    for (let i = 0; i < n; i++) {
      out.push(makeEmail(t));
      t += rand(2, 22);
    }
    return out.sort((a, b) => new Date(b.ts) - new Date(a.ts));
  }

  function fmtTime(iso) {
    const d = new Date(iso);
    const p = (x) => String(x).padStart(2, "0");
    return `${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`;
  }
  function fmtDateTime(iso) {
    const d = new Date(iso);
    const p = (x) => String(x).padStart(2, "0");
    return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`;
  }
  function relTime(iso) {
    const s = Math.floor((Date.now() - new Date(iso)) / 1000);
    if (s < 60) return `${s}초 전`;
    if (s < 3600) return `${Math.floor(s / 60)}분 전`;
    if (s < 86400) return `${Math.floor(s / 3600)}시간 전`;
    return `${Math.floor(s / 86400)}일 전`;
  }

  // 시간대별 통계 (24시간)
  function hourlyStats() {
    const out = [];
    for (let h = 0; h < 24; h++) {
      const base = h >= 9 && h <= 18 ? rand(18, 46) : rand(3, 16);
      const total = Math.round(base);
      const q = Math.round(total * rand(0.12, 0.3));
      const r = Math.round(total * rand(0.08, 0.18));
      out.push({ hour: h, total, quarantined: q, review: r, normal: total - q - r });
    }
    return out;
  }

  // 자동 대응 로그
  function makeActionLog(feed) {
    const ACTIONS = {
      quarantined: { label: "Quarantine label 적용 + INBOX 제거", tone: "danger" },
      review: { label: "Needs-Review label 부여", tone: "warn" },
      normal: { label: "INBOX 유지 (조치 없음)", tone: "ok" },
    };
    return feed.map((e) => ({
      id: e.id,
      ts: e.ts,
      actor: "Action Engine",
      subject: e.subject,
      from: e.from,
      status: e.status,
      action: ACTIONS[e.status].label,
      tone: ACTIONS[e.status].tone,
      final: e.final,
      latency: e.latency,
    }));
  }

  const FEED = makeFeed(46);
  const HOURLY = hourlyStats();
  const LOG = makeActionLog(FEED);

  window.SOC = {
    FEED,
    HOURLY,
    LOG,
    URL_FEATURES,
    STATUS_META,
    statusFromScore,
    makeEmail,
    fmtTime,
    fmtDateTime,
    relTime,
    // 누적 KPI
    kpi() {
      const total = FEED.length;
      const q = FEED.filter((e) => e.status === "quarantined").length;
      const r = FEED.filter((e) => e.status === "review").length;
      const n = total - q - r;
      const avgLat = (FEED.reduce((s, e) => s + e.latency, 0) / total).toFixed(1);
      return { total, q, r, n, avgLat, fpr: 1.8, fnr: 0.9, throughput: 142 };
    },
  };
})();
