import { useState } from "react";
import { loginWithGoogle } from "../api/auth.js";
import { Icon } from "../components/Icon.jsx";
import { Logo } from "../components/Logo.jsx";

export function LoginPage() {
  const [loading, setLoading] = useState(false);
  function handleLogin() {
    setLoading(true);
    loginWithGoogle();
  }

  return (
    <main className="login-page">
      <section className="login-hero">
        <div className="brand login-brand">
          <Logo size={38} />
          <div>
            <strong>PhishGuard <span>SOC</span></strong>
            <small>피싱 메일 자동 분석·격리 시스템</small>
          </div>
        </div>
        <div className="login-copy">
          <h1>메일이 도착하는 순간,<br /><span>자동으로 분석하고 격리</span>합니다.</h1>
          <p>Gmail API Webhook과 Ensemble AI로 본문 문맥과 URL 구조를 동시에 분석해 피싱 위험도를 산출하고 SOC 대시보드에 실시간 기록합니다.</p>
          <div className="tech-tags">
            {["Gmail API + Pub/Sub", "BERT NLP", "XGBoost URL", "Ensemble Risk"].map((item) => <span className="mono" key={item}>{item}</span>)}
          </div>
        </div>
        <small>event-driven security automation · 2026</small>
      </section>
      <section className="login-panel">
        <div>
          <h2>SOC 대시보드 로그인</h2>
          <p>모니터링 대상 Gmail 계정으로 인증합니다. 로그인 후 Gmail watch가 등록되고 JWT 세션이 발급됩니다.</p>
          <button className="google-btn" onClick={handleLogin} disabled={loading}>
            {loading ? <span className="spinner" /> : <Icon name="shield" size={20} />}
            {loading ? "Gmail watch 등록 중..." : "Google 계정으로 로그인"}
          </button>
          <div className="login-steps">
            <strong>로그인 시 자동 수행</strong>
            <span><Icon name="mail" size={15} />Gmail OAuth 토큰 저장</span>
            <span><Icon name="bell" size={15} />Gmail watch 및 Pub/Sub 연결</span>
            <span><Icon name="shield" size={15} />JWT Access + Refresh 발급</span>
          </div>
        </div>
      </section>
    </main>
  );
}
