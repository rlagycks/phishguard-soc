import { useEffect, useState } from "react";
import { captureAuthFromUrl, clearTokens, verifySession } from "./api/auth.js";
import { DetailDrawer } from "./components/DetailDrawer.jsx";
import { Shell } from "./components/Layout.jsx";
import { DashboardPage } from "./pages/DashboardPage.jsx";
import { ListPageFallback } from "./pages/ListPageFallback.jsx";
import { LoginPage } from "./pages/LoginPage.jsx";
import { LogsPage } from "./pages/LogsPage.jsx";
import { MailListPage } from "./pages/MailListPage.jsx";
import { StatsPage } from "./pages/StatsPage.jsx";

export function App() {
  const [checking, setChecking] = useState(true);
  const [user, setUser] = useState(null);
  const [route, setRoute] = useState("dashboard");
  const [live, setLive] = useState(true);
  const [selectedId, setSelectedId] = useState(null);
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    captureAuthFromUrl();
    verifySession()
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setChecking(false));
  }, []);

  function logout() {
    clearTokens();
    window.location.href = "/";
  }

  if (checking) return <div className="boot-screen">SOC 세션을 확인하는 중입니다.</div>;
  if (!user) return <LoginPage />;

  return (
    <Shell route={route} setRoute={setRoute} userEmail={user.email} onLogout={logout} live={live} setLive={setLive}>
      {route === "dashboard" && <DashboardPage key={`dashboard-${refreshKey}`} live={live} onSelect={setSelectedId} />}
      {route === "list" && <MailListPage key={`list-${refreshKey}`} onSelect={setSelectedId} />}
      {route === "logs" && <LogsPage key={`logs-${refreshKey}`} onSelect={setSelectedId} />}
      {route === "stats" && <StatsPage />}
      {!["dashboard", "list", "logs", "stats"].includes(route) && <ListPageFallback />}
      {selectedId && (
        <DetailDrawer
          emailId={selectedId}
          onClose={() => setSelectedId(null)}
          onChanged={() => setRefreshKey((value) => value + 1)}
        />
      )}
    </Shell>
  );
}
