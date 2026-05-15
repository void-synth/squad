"use client";

import { useEffect, useRef, useState } from "react";
import { Button, Input, Spinner } from "@heroui/react";
import { useAgent } from "../../context/AgentContext.jsx";

export default function AgentChat() {
  const { messages, sendMessage, sending, chatError, clearChatError, apiOnline } = useAgent();
  const [input, setInput] = useState("");
  const scrollRef = useRef(null);

  useEffect(() => {
    const el = scrollRef.current;
    if (el) {
      el.scrollTop = el.scrollHeight;
    }
  }, [messages, sending]);

  const submit = () => {
    const trimmed = input.trim();
    if (!trimmed || sending) return;
    clearChatError();
    void sendMessage(trimmed);
    setInput("");
  };

  return (
    <div className="flex min-h-[320px] flex-col gap-3">
      <div
        ref={scrollRef}
        className="border-default-200/60 flex max-h-[min(420px,50vh)] min-h-[220px] flex-col gap-2 overflow-y-auto rounded-xl border bg-content2/30 p-3"
        aria-live="polite"
        aria-relevant="additions"
      >
        {messages.map((m, i) => (
          <div
            key={m.id ?? `${i}-${m.role}-${m.content?.slice(0, 24)}`}
            className={
              m.role === "user"
                ? "bg-primary/15 border-primary/20 ml-6 max-w-[92%] self-end rounded-xl border px-3 py-2 text-sm whitespace-pre-wrap"
                : "bg-content1 border-default-200/60 mr-6 max-w-[92%] self-start rounded-xl border px-3 py-2 text-sm whitespace-pre-wrap"
            }
          >
            {m.content}
          </div>
        ))}
        {sending ? (
          <div className="text-default-500 mr-6 flex max-w-[92%] items-center gap-2 self-start rounded-xl border border-default-200/60 bg-content1 px-3 py-2 text-sm">
            <Spinner size="sm" color="primary" />
            <span>Titan is thinking…</span>
          </div>
        ) : null}
      </div>

      {apiOnline === false ? (
        <p className="text-warning text-xs" role="status">
          Backend offline — start uvicorn on port 8000 (see README), then refresh.
        </p>
      ) : null}
      {chatError ? (
        <p className="text-danger text-xs" role="alert">
          {chatError}
        </p>
      ) : null}

      <form
        className="relative z-10 flex gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          submit();
        }}
      >
        <Input
          name="agent-message"
          type="text"
          autoComplete="off"
          placeholder="Ask Titan anything — greetings, flagged transfers, Bolu & Daniel…"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              submit();
            }
          }}
          className="min-w-0 flex-1"
          size="sm"
          isDisabled={sending}
          aria-label="Message to Titan"
        />
        <Button
          type="submit"
          color="primary"
          size="sm"
          isLoading={sending}
          isDisabled={sending || !input.trim()}
        >
          Send
        </Button>
      </form>
    </div>
  );
}
