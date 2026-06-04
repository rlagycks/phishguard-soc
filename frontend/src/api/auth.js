const ACCESS_KEY = "soc_access_token";
const REFRESH_KEY = "soc_refresh_token";

export function captureAuthFromUrl() {
  const params = new URLSearchParams(window.location.search);
  const access = params.get("access_token");
  const refresh = params.get("refresh_token");
  if (!access) return false;

  localStorage.setItem(ACCESS_KEY, access);
  if (refresh) localStorage.setItem(REFRESH_KEY, refresh);

  const cleanUrl = `${window.location.origin}${window.location.pathname}`;
  window.history.replaceState({}, document.title, cleanUrl);
  return true;
}

export function getAccessToken() {
  return localStorage.getItem(ACCESS_KEY) || "";
}

export function getRefreshToken() {
  return localStorage.getItem(REFRESH_KEY) || "";
}

export function clearTokens() {
  localStorage.removeItem(ACCESS_KEY);
  localStorage.removeItem(REFRESH_KEY);
}

export async function verifySession() {
  const token = getAccessToken();
  if (!token) return null;

  const res = await fetch("/auth/verify", {
    headers: { Authorization: `Bearer ${token}` }
  });
  if (res.ok) return res.json();
  if (res.status !== 401) return null;

  const refresh = getRefreshToken();
  if (!refresh) return null;

  const refreshRes = await fetch("/auth/refresh", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refresh })
  });
  if (!refreshRes.ok) return null;

  const body = await refreshRes.json();
  localStorage.setItem(ACCESS_KEY, body.access_token);
  return verifySession();
}

export function loginWithGoogle() {
  window.location.href = "/auth/login";
}
