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
  // Carried forward from the active message's own tracked fields, not
  // re-derived from the raw event stream - see CounterDisplayProps
  // (Brew 39, docs/design/counter-scene-design.md Section 3.2).
  const beanAlias = activeMessage?.role === "assistant" ? activeMessage.beanAlias : null;
  const complexity = activeMessage?.role === "assistant" ? activeMessage.complexity : null;
  const hasVisibleContent =
    activeMessage?.role === "assistant" ? activeMessage.content.length > 0 : false;

  return (
    <div className="flex h-screen flex-col">
      <div className="flex flex-1 overflow-hidden">
        <Sidebar />
        <div className="flex flex-1 flex-col overflow-hidden">
          <div className="flex flex-1 overflow-hidden">
            <ResponseSection />
            <CounterDisplay
              event={latestEvent}
              sessionCostUsd={sessionCostUsd}
              beanAlias={beanAlias}
              complexity={complexity}
              hasVisibleContent={hasVisibleContent}
            />
          </div>
          <OrderBox />
        </div>
      </div>
      <CommandPalette />
    </div>
  );
}
