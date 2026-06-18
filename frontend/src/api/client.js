import { clearTokens, getAccessToken, refreshAccessToken } from "./auth.js";
import { adaptEmailDetail, adaptEmailSummary, adaptStats } from "./adapters.js";

// Shared refresh promise so concurrent 401s don't each trigger a separate refresh
let _refreshPromise = null;

async function request(path, options = {}) {
  const token = getAccessToken();
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };
  if (token) headers.Authorization = `Bearer ${token}`;

  const res = await fetch(path, { ...options, headers });

  if (res.status === 401 && !options._retried) {
    if (!_refreshPromise) {
      _refreshPromise = refreshAccessToken().finally(() => { _refreshPromise = null; });
    }
    const ok = await _refreshPromise;
    if (ok) return request(path, { ...options, _retried: true });
    clearTokens();
    window.location.href = "/auth/login";
    throw new Error("Session expired");
  }

  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `Request failed: ${res.status}`);
  }
  return res.json();
}

export async function fetchStats() {
  return adaptStats(await request("/api/dashboard/stats"));
}

export async function fetchEmails(params = {}) {
  const query = new URLSearchParams();
  if (params.status && params.status !== "all") query.set("status", params.status);
  if (params.riskLevel && params.riskLevel !== "all") query.set("risk_level", params.riskLevel);
  query.set("limit", String(params.limit || 80));
  const suffix = query.toString() ? `?${query}` : "";
  const rows = await request(`/api/dashboard/emails${suffix}`);
  return rows.map(adaptEmailSummary);
}

export async function fetchEmailDetail(id) {
  return adaptEmailDetail(await request(`/api/dashboard/emails/${id}`));
}

export async function updateEmailStatus(id, status) {
  return adaptEmailDetail(
    await request(`/api/dashboard/emails/${id}/status`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    })
  );
}

export async function fetchActionLogs() {
  return request("/api/dashboard/action-logs");
}

export async function fetchHourlyStats() {
  return request("/api/dashboard/hourly");
}

export async function fetchSystemHealth() {
  return request("/api/dashboard/system-health");
}

export async function fetchModelPerformance() {
  return request("/api/dashboard/model-performance");
}
