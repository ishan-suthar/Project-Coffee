"use client";

import { useChatStore } from "@/store/chatStore";
import { Sidebar } from "@/components/Sidebar";
import { CounterDisplay } from "@/components/CounterDisplay";
import { ResponseSection } from "@/components/ResponseSection";
import { OrderBox } from "@/components/OrderBox";
import { CommandPalette } from "@/components/CommandPalette";

export default function Home() {
  const activeMessage = useChatStore((s) => {
    const messages = s.activeSessionId ? s.messages[s.activeSessionId] ?? [] : [];
    return messages.length > 0 ? messages[messages.length - 1] : null;
  });

  const latestEvent = activeMessage?.role === "assistant" ? activeMessage.latestEvent : null;
  const sessionCostUsd =
    latestEvent?.event === "generating"
      ? latestEvent.est_cost_usd ?? 0
      : activeMessage?.costUsd ?? 0;

  return (
    <div className="flex h-screen flex-col">
      <CounterDisplay event={latestEvent} sessionCostUsd={sessionCostUsd} />
      <div className="flex flex-1 overflow-hidden">
        <Sidebar />
        <div className="flex flex-1 flex-col overflow-hidden">
          <ResponseSection />
          <OrderBox />
        </div>
      </div>
      <CommandPalette />
    </div>
  );
}
