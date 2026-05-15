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
import { useRouter } from "next/navigation";
import { formatApiError, getAgentMemory, getHealth, postAgentChat } from "../services/api.js";
import { createDashboardSocket } from "../services/socket.js";
import { useDashboard } from "./DashboardContext.jsx";
import { buildActiveThoughts } from "../components/agent/agentNeuralUtils.js";

const AgentContext = createContext(null);

const GREETING =
  "I'm Titan, your fraud ops agent. Ask about transfers, links between senders, or say “show flagged” to filter the feed.";

let messageSeq = 0;
function nextMessageId() {
  messageSeq += 1;
  return `msg-${Date.now()}-${messageSeq}`;
}

export function AgentProvider({ children }) {
  const router = useRouter();
  const { setTransactionStatusFilter, setActiveAlert, alerts, setHighlightedRef } = useDashboard();

  const [messages, setMessages] = useState([
    { id: nextMessageId(), role: "assistant", content: GREETING },
  ]);
  const [avatarState, setAvatarState] = useState("idle");
  const [sessionId, setSessionId] = useState(null);
  const [memory, setMemory] = useState(null);
  const [memoryLoading, setMemoryLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [chatError, setChatError] = useState(null);
  const [apiOnline, setApiOnline] = useState(null);
  const [tab, setTab] = useState("chat");
  const sessionRef = useRef(null);
  const chatInFlightRef = useRef(false);

  const loadMemory = useCallback(async () => {
    setMemoryLoading(true);
    try {
      const data = await getAgentMemory();
      setMemory(data);
    } catch (e) {
      console.error("Agent memory load failed", e);
    } finally {
      setMemoryLoading(false);
    }
  }, []);

  const clearChatError = useCallback(() => setChatError(null), []);

  const appendMessage = useCallback((role, content, extra = {}) => {
    setMessages((prev) => [...prev, { id: nextMessageId(), role, content, ...extra }]);
  }, []);

  useEffect(() => {
    void loadMemory();
  }, [loadMemory]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        await getHealth();
        if (!cancelled) setApiOnline(true);
      } catch {
        if (!cancelled) setApiOnline(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    const s = createDashboardSocket();
    s.on("agent_message", (payload) => {
      if (!payload?.content) return;
      if (payload.auto) {
        appendMessage("assistant", payload.content, { auto: true });
        return;
      }
      if (chatInFlightRef.current) return;
      appendMessage("assistant", payload.content);
    });
    s.on("agent_state", (payload) => {
      if (payload?.state) setAvatarState(payload.state);
    });
    s.on("agent_action", (action) => {
      if (!action?.type) return;
      if (action.type === "navigate" && action.path) {
        router.push(action.path);
      } else if (action.type === "pin_alert" && action.alert_id != null) {
        const row = alerts.find((a) => a.id === action.alert_id);
        if (row) setActiveAlert(row);
      } else if (action.type === "filter_transactions") {
        setTransactionStatusFilter(action.status ?? null);
      } else if (action.type === "highlight_transaction" && action.transaction_ref) {
        setHighlightedRef(action.transaction_ref);
      }
    });
    s.on("new_transaction", () => {
      void loadMemory();
    });
    s.connect();
    return () => s.disconnect();
  }, [alerts, appendMessage, loadMemory, router, setActiveAlert, setHighlightedRef, setTransactionStatusFilter]);

  const applyActions = useCallback(
    (actions) => {
      if (!Array.isArray(actions)) return;
      for (const action of actions) {
        if (action.type === "navigate" && action.path) router.push(action.path);
        if (action.type === "filter_transactions") setTransactionStatusFilter(action.status ?? null);
        if (action.type === "pin_alert" && action.alert_id != null) {
          const row = alerts.find((a) => a.id === action.alert_id);
          if (row) setActiveAlert(row);
        }
        if (action.type === "highlight_transaction" && action.transaction_ref) {
          setHighlightedRef(action.transaction_ref);
        }
      }
    },
    [alerts, router, setActiveAlert, setHighlightedRef, setTransactionStatusFilter]
  );

  const activeThoughts = useMemo(
    () => buildActiveThoughts({ memory, messages, sending, avatarState }),
    [memory, messages, sending, avatarState]
  );

  const sendMessage = useCallback(
    async (text) => {
      const trimmed = (text || "").trim();
      if (!trimmed || sending) return;

      setChatError(null);
      setSending(true);
      chatInFlightRef.current = true;
      setAvatarState("thinking");
      appendMessage("user", trimmed);

      try {
        const res = await postAgentChat({
          message: trimmed,
          session_id: sessionRef.current || sessionId,
        });
        if (res.session_id) {
          sessionRef.current = res.session_id;
          setSessionId(res.session_id);
        }
        const reply = (res.reply || "").trim();
        if (reply) {
          appendMessage("assistant", reply);
        }
        applyActions(res.actions);
      } catch (e) {
        const err = formatApiError(e);
        setChatError(err);
        appendMessage("assistant", `Sorry, I couldn't reach the server: ${err}`);
      } finally {
        chatInFlightRef.current = false;
        setSending(false);
        setAvatarState("idle");
      }
    },
    [appendMessage, applyActions, sending, sessionId]
  );

  const value = useMemo(
    () => ({
      messages,
      avatarState,
      sending,
      chatError,
      clearChatError,
      apiOnline,
      tab,
      setTab,
      memory,
      memoryLoading,
      activeThoughts,
      sendMessage,
      loadMemory,
    }),
    [
      messages,
      avatarState,
      sending,
      chatError,
      clearChatError,
      apiOnline,
      tab,
      memory,
      memoryLoading,
      activeThoughts,
      sendMessage,
      loadMemory,
    ]
  );

  return <AgentContext.Provider value={value}>{children}</AgentContext.Provider>;
}

export function useAgent() {
  const ctx = useContext(AgentContext);
  if (!ctx) throw new Error("useAgent must be used within AgentProvider");
  return ctx;
}
