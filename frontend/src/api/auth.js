const ACCESS_KEY = "soc_access_token";
const REFRESH_KEY = "soc_refresh_token";

let _refreshTimer = null;

function _getTokenExpiry(token) {
  try {
    return JSON.parse(atob(token.split(".")[1])).exp * 1000;
  } catch {
    return null;
  }
}

function _cancelRefreshTimer() {
  if (_refreshTimer !== null) {
    clearTimeout(_refreshTimer);
    _refreshTimer = null;
  }
}

export async function refreshAccessToken() {
  const refresh = getRefreshToken();
  if (!refresh) return false;
  try {
    const res = await fetch("/auth/refresh", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refresh }),
    });
    if (!res.ok) return false;
    const body = await res.json();
    localStorage.setItem(ACCESS_KEY, body.access_token);
    scheduleTokenRefresh(body.access_token);
    return true;
  } catch {
    return false;
  }
}

export function scheduleTokenRefresh(token) {
  _cancelRefreshTimer();
  const expiry = _getTokenExpiry(token);
  if (!expiry) return;
  const delay = expiry - Date.now() - 60_000; // refresh 60s before expiry
  if (delay <= 0) {
    refreshAccessToken();
    return;
  }
  _refreshTimer = setTimeout(refreshAccessToken, delay);
}

export function captureAuthFromUrl() {
  const params = new URLSearchParams(window.location.search);
  const access = params.get("access_token");
  const refresh = params.get("refresh_token");
  if (!access) return false;

  localStorage.setItem(ACCESS_KEY, access);
  if (refresh) localStorage.setItem(REFRESH_KEY, refresh);

  const cleanUrl = `${window.location.origin}${window.location.pathname}`;
  window.history.replaceState({}, document.title, cleanUrl);
  scheduleTokenRefresh(access);
  return true;
}

export function getAccessToken() {
  return localStorage.getItem(ACCESS_KEY) || "";
}

export function getRefreshToken() {
  return localStorage.getItem(REFRESH_KEY) || "";
}

export function clearTokens() {
  _cancelRefreshTimer();
  localStorage.removeItem(ACCESS_KEY);
  localStorage.removeItem(REFRESH_KEY);
}

export async function verifySession() {
  const token = getAccessToken();
  if (!token) return null;

  const res = await fetch("/auth/verify", {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (res.ok) {
    scheduleTokenRefresh(token);
    return res.json();
  }
  if (res.status !== 401) return null;

  const refreshed = await refreshAccessToken();
  if (!refreshed) return null;
  return verifySession();
}

export function loginWithGoogle() {
  window.location.href = "/auth/login";
}
