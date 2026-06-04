import { Activity, BarChart3, Grid2X2, List } from "lucide-react";
import { Logo } from "./Logo.jsx";
import { Icon } from "./Icon.jsx";

const NAV = [
  { key: "dashboard", label: "대시보드", icon: Grid2X2 },
  { key: "list", label: "위험 메일 목록", icon: List },
  { key: "logs", label: "자동 대응 로그", icon: Activity },
  { key: "stats", label: "통계 / 성능", icon: BarChart3 }
];

const TITLES = {
  dashboard: ["실시간 탐지 현황", "메일 수신 이벤트를 트리거로 자동 분석·격리합니다"],
  list: ["위험 메일 목록", "최종 위험도 기준으로 정렬·필터링합니다"],
  logs: ["자동 대응 로그", "Quarantine / Needs-Review / Normal 처리 내역"],
  stats: ["통계 / 성능", "탐지 성능, 처리 시간, 모델별 비교 지표"]
};

export function Shell({ route, setRoute, userEmail, onLogout, live, setLive, children }) {
  const [title, subtitle] = TITLES[route] || TITLES.dashboard;
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <Logo />
          <div>
            <strong>PhishGuard <span>SOC</span></strong>
            <small>Security Automation</small>
          </div>
        </div>
        <nav className="nav">
          <p>관제</p>
          {NAV.map((item) => {
            const ActiveIcon = item.icon;
            const active = route === item.key;
            return (
              <button className={active ? "active" : ""} key={item.key} onClick={() => setRoute(item.key)}>
                <ActiveIcon size={18} strokeWidth={1.8} />
                {item.label}
              </button>
            );
          })}
        </nav>
        <div className="sidebar-user">
          <div className="avatar">S</div>
          <div>
            <strong>soc-analyst</strong>
            <small className="mono">{userEmail || "phishing-report@gmail.com"}</small>
          </div>
          <button className="icon-btn" onClick={onLogout} title="로그아웃"><Icon name="logout" size={15} /></button>
        </div>
      </aside>
      <section className="workspace">
        <header className="topbar">
          <div className="route-title">
            <h1>{title}</h1>
            <p>{subtitle}</p>
          </div>
          <div className="topbar-actions">
            <button className="btn sm" onClick={() => setLive((value) => !value)}>
              <span className={`live-dot ${live ? "" : "paused"}`} />
              {live ? "라이브 ON" : "일시정지"}
            </button>
            <button className="icon-btn" title="알림"><Icon name="bell" size={17} /><span className="notify-dot" /></button>
          </div>
        </header>
        <main className="content">{children}</main>
      </section>
    </div>
  );
}
