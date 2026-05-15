import axios from "axios";

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || "",
});

/**
 * Human-readable message from FastAPI / axios errors (never touches auth).
 */
export function formatApiError(error) {
  const d = error?.response?.data?.detail;
  if (d == null) return error?.message || "Request failed";
  if (typeof d === "string") return d;
  if (Array.isArray(d)) {
    return d
      .map((x) => (typeof x === "object" && x?.msg != null ? String(x.msg) : JSON.stringify(x)))
      .join("; ");
  }
  if (typeof d === "object" && d?.error != null) return String(d.error);
  try {
    return JSON.stringify(d);
  } catch {
    return "Request failed";
  }
}

export async function getHealth() {
  const { data } = await api.get("/api/v1/health");
  return data;
}

export async function getSquadIntegrationStatus() {
  const { data } = await api.get("/api/v1/integration/squad/status");
  return data;
}

export async function getIntegrationQueue() {
  const { data } = await api.get("/api/v1/integration/queue");
  return data;
}

export async function squadVerifyTransaction(transactionRef) {
  const { data } = await api.get(
    `/api/v1/integration/squad/verify/${encodeURIComponent(transactionRef)}`
  );
  return data;
}

export async function createSquadVirtualAccount(body) {
  const { data } = await api.post("/api/v1/integration/squad/virtual-account", body);
  return data;
}

export async function squadPayout(body) {
  const { data } = await api.post("/api/v1/integration/squad/payout", body);
  return data;
}

export async function initiateSquadCheckout(body) {
  const { data } = await api.post("/api/v1/integration/squad/checkout/initiate", body);
  return data;
}

export async function getTransactions(params = {}) {
  const { data } = await api.get("/api/v1/transactions", { params });
  return data;
}

export async function getAlerts(params = {}) {
  const { data } = await api.get("/api/v1/alerts", { params });
  return data;
}

export async function getStats() {
  const { data } = await api.get("/api/v1/stats");
  return data;
}

export async function getTransactionDetail(ref) {
  const { data } = await api.get(`/api/v1/transactions/${encodeURIComponent(ref)}`);
  return data;
}

export async function releaseAlert(id, body) {
  const { data } = await api.post(`/api/v1/alerts/${id}/release`, body);
  return data;
}

export async function escalateAlert(id, body) {
  const { data } = await api.post(`/api/v1/alerts/${id}/escalate`, body);
  return data;
}

export async function postAgentChat(body) {
  const { data } = await api.post("/api/v1/agent/chat", body);
  return data;
}

export async function getAgentMemory() {
  const { data } = await api.get("/api/v1/agent/memory");
  return data;
}
