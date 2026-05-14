"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import {
  escalateAlert as apiEscalate,
  formatApiError,
  getAlerts,
  getStats,
  getTransactions,
  releaseAlert as apiRelease,
} from "../services/api.js";
import { createDashboardSocket } from "../services/socket.js";
import { normalizeAlert, pickDisplayedAlert } from "../utils/alertNormalize.js";

const DashboardContext = createContext(null);

export function DashboardProvider({ children }) {
  const [transactions, setTransactions] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [stats, setStats] = useState({});
  const [isConnected, setConnected] = useState(false);
  const [pinnedAlertId, setPinnedAlertId] = useState(null);
  const [transactionStatusFilter, setTransactionStatusFilter] = useState(null);
  const [bootstrapError, setBootstrapError] = useState(null);
  const [transactionsLoading, setTransactionsLoading] = useState(true);
  const [retryToken, setRetryToken] = useState(0);

  const socketRef = useRef(null);
  const txFilterRef = useRef(transactionStatusFilter);
  const didDisconnectRef = useRef(false);

  txFilterRef.current = transactionStatusFilter;

  const activeAlert = useMemo(
    () => pickDisplayedAlert(alerts, pinnedAlertId),
    [alerts, pinnedAlertId]
  );

  const setActiveAlert = useCallback((row) => {
    if (row == null) {
      setPinnedAlertId(null);
      return;
    }
    const id = row.alert_id ?? row.id;
    if (id != null) setPinnedAlertId(id);
  }, []);

  useEffect(() => {
    if (process.env.NODE_ENV === "development") {
      if (!process.env.NEXT_PUBLIC_API_URL) {
        console.warn("[Titan] NEXT_PUBLIC_API_URL is unset; API calls use same-origin.");
      }
      if (!process.env.NEXT_PUBLIC_SOCKET_URL) {
        console.warn("[Titan] NEXT_PUBLIC_SOCKET_URL is unset; Socket.IO uses same-origin.");
      }
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setBootstrapError(null);
      setTransactionsLoading(true);
      const txParams = transactionStatusFilter ? { status: transactionStatusFilter } : {};
      try {
        const [tx, al, st] = await Promise.all([
          getTransactions(txParams),
          getAlerts({ resolved: false }),
          getStats(),
        ]);
        if (cancelled) return;
        setTransactions(Array.isArray(tx) ? tx : []);
        setAlerts(Array.isArray(al) ? al.map((a) => normalizeAlert(a)).filter(Boolean) : []);
        setStats(st || {});
      } catch (e) {
        if (cancelled) return;
        setBootstrapError(formatApiError(e));
        console.error("Dashboard data load failed", e);
      } finally {
        if (!cancelled) setTransactionsLoading(false);
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [transactionStatusFilter, retryToken]);

  const retryBootstrap = useCallback(() => {
    setRetryToken((n) => n + 1);
  }, []);

  const refetchAfterReconnect = useCallback(async () => {
    const txParams = txFilterRef.current ? { status: txFilterRef.current } : {};
    try {
      const [tx, al, st] = await Promise.all([
        getTransactions(txParams),
        getAlerts({ resolved: false }),
        getStats(),
      ]);
      setTransactions(Array.isArray(tx) ? tx : []);
      setAlerts(Array.isArray(al) ? al.map((a) => normalizeAlert(a)).filter(Boolean) : []);
      setStats(st || {});
    } catch (e) {
      console.error("Reconnect refetch failed", e);
    }
  }, []);

  useEffect(() => {
    const s = createDashboardSocket();
    socketRef.current = s;

    s.on("connect", () => {
      setConnected(true);
      if (didDisconnectRef.current) {
        didDisconnectRef.current = false;
        void refetchAfterReconnect();
      }
    });
    s.on("disconnect", () => {
      setConnected(false);
      didDisconnectRef.current = true;
    });

    s.on("new_transaction", (payload) => {
      const filter = txFilterRef.current;
      if (filter && payload.status !== filter) return;
      setTransactions((prev) => {
        const next = [payload, ...prev.filter((t) => t.transaction_ref !== payload.transaction_ref)];
        return next.slice(0, 300);
      });
    });

    s.on("fraud_alert", (payload) => {
      const normalized = normalizeAlert({
        id: payload.alert_id,
        alert_id: payload.alert_id,
        risk_score: payload.risk_score,
        alert_level: payload.alert_level,
        reason: payload.reason,
        pattern_type: payload.pattern_type,
        action_taken: payload.action_taken,
        transaction_ref: payload.transaction_ref,
        sender_account: payload.sender_account,
        sender_bank: payload.sender_bank,
        receiver_account: payload.receiver_account,
        receiver_bank: payload.receiver_bank,
        amount_naira: payload.amount_naira,
        created_at: payload.created_at,
        resolved_at: payload.resolved_at ?? null,
        resolved_by: payload.resolved_by ?? "",
        transaction: payload.transaction,
      });
      if (!normalized) return;
      setAlerts((prev) => {
        const rest = prev.filter((a) => a.id !== normalized.id);
        return [normalized, ...rest].slice(0, 50);
      });
    });

    s.on("stats_update", (payload) => {
      setStats(payload || {});
    });

    s.connect();
    return () => {
      s.disconnect();
      socketRef.current = null;
    };
  }, [refetchAfterReconnect]);

  const releaseAlert = useCallback(async (id, body) => {
    const res = await apiRelease(id, body);
    setAlerts((prev) =>
      prev.map((a) =>
        a.id === id
          ? normalizeAlert({
              ...a,
              action_taken: res.action_taken,
              resolved_by: res.resolved_by,
              resolved_at: res.resolved_at,
              transaction: res.transaction || a.transaction,
            })
          : a
      )
    );
    setPinnedAlertId((p) => (p === id ? null : p));
    const st = await getStats();
    setStats(st);
    return res;
  }, []);

  const escalateAlert = useCallback(async (id, body) => {
    const res = await apiEscalate(id, body);
    setAlerts((prev) =>
      prev.map((a) =>
        a.id === id
          ? normalizeAlert({
              ...a,
              action_taken: res.action_taken,
              resolved_by: res.resolved_by,
              resolved_at: res.resolved_at,
              transaction: res.transaction || a.transaction,
            })
          : a
      )
    );
    setPinnedAlertId((p) => (p === id ? null : p));
    const st = await getStats();
    setStats(st);
    return res;
  }, []);

  const value = useMemo(
    () => ({
      transactions,
      alerts,
      stats,
      isConnected,
      activeAlert,
      setActiveAlert,
      releaseAlert,
      escalateAlert,
      transactionStatusFilter,
      setTransactionStatusFilter,
      bootstrapError,
      transactionsLoading,
      retryBootstrap,
    }),
    [
      transactions,
      alerts,
      stats,
      isConnected,
      activeAlert,
      setActiveAlert,
      releaseAlert,
      escalateAlert,
      transactionStatusFilter,
      bootstrapError,
      transactionsLoading,
      retryBootstrap,
    ]
  );

  return <DashboardContext.Provider value={value}>{children}</DashboardContext.Provider>;
}

export function useDashboard() {
  const ctx = useContext(DashboardContext);
  if (!ctx) throw new Error("useDashboard must be used within DashboardProvider");
  return ctx;
}
