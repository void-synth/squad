import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "",
});

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
