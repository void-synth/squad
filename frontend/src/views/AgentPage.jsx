"use client";

import dynamic from "next/dynamic";
import { Button } from "@heroui/react";
import AgentChat from "../components/agent/AgentChat.jsx";
import AgentMemory from "../components/agent/AgentMemory.jsx";
import AgentNeural from "../components/agent/AgentNeural.jsx";
import { useAgent } from "../context/AgentContext.jsx";

const AgentAvatar = dynamic(() => import("../components/agent/AgentAvatar.jsx"), {
  ssr: false,
  loading: () => (
    <div className="flex h-[min(500px,62vh)] min-h-[420px] items-center justify-center text-sm text-default-500">
      Loading agent…
    </div>
  ),
});

const TAB_PANELS = {
  chat: AgentChat,
  memory: AgentMemory,
  neural: AgentNeural,
};

export default function AgentPage() {
  const { tab, setTab } = useAgent();
  const Panel = TAB_PANELS[tab] || AgentChat;

  return (
    <div className="flex w-full flex-col px-3 py-4 sm:px-6">
      <header className="mb-4">
        <p className="text-default-500 text-[0.65rem] font-bold uppercase tracking-[0.2em]">Live agent</p>
        <h1 className="text-default-foreground text-xl font-bold">Titan AI</h1>
        <p className="text-default-500 mt-1 max-w-2xl text-sm">
          Chat with the agent, inspect memory links, or explore the neural view of live fraud memory.
        </p>
      </header>

      <div className="mb-4 flex flex-wrap gap-2">
        <Button size="sm" variant={tab === "chat" ? "solid" : "flat"} color="primary" onPress={() => setTab("chat")}>
          Chat
        </Button>
        <Button size="sm" variant={tab === "memory" ? "solid" : "flat"} color="primary" onPress={() => setTab("memory")}>
          Memory
        </Button>
        <Button size="sm" variant={tab === "neural" ? "solid" : "flat"} color="primary" onPress={() => setTab("neural")}>
          Neural Network
        </Button>
      </div>

      <div className="grid items-start gap-6 xl:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)]">
        <AgentAvatar className="xl:sticky xl:top-4" />
        <div className="relative z-10 min-w-0">
          <Panel />
        </div>
      </div>
    </div>
  );
}
