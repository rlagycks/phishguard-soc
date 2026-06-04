import { getAccessToken } from "./auth.js";
import { adaptEmailDetail, adaptEmailSummary, adaptStats } from "./adapters.js";

async function request(path, options = {}) {
  const token = getAccessToken();
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {})
  };
  if (token) headers.Authorization = `Bearer ${token}`;

  const res = await fetch(path, { ...options, headers });
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
      body: JSON.stringify({ status })
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
