"use client";

import { useState } from "react";
import { useChatStore } from "@/store/chatStore";
import { Sidebar } from "@/components/Sidebar";
import { CounterDisplay } from "@/components/CounterDisplay";
import { ResponseSection } from "@/components/ResponseSection";
import { OrderBox } from "@/components/OrderBox";
import { CommandPalette } from "@/components/CommandPalette";

export default function Home() {
  // Mobile-only (<768px) slide-over drawer state for Sidebar - unused at
  // md and up, where Sidebar renders in-flow exactly as before. Plain
  // component state, not the chat store: this is ephemeral UI state, not
  // session/business data.
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);

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
    <div className="app-shell-height flex w-full max-w-full flex-col overflow-x-hidden">
      {/* Mobile-only (<768px) header with the sidebar drawer toggle - at
          md and up this is hidden entirely and Sidebar renders in its
          normal in-flow position instead, exactly as before this change.
          pt-[env(safe-area-inset-top)] clears the iPhone notch/status bar
          since this header is the top-most fixed element in the shell. */}
      <header
        className="flex shrink-0 items-center gap-2 border-b border-caramel bg-latte px-3 py-2 md:hidden"
        style={{ paddingTop: "calc(0.5rem + env(safe-area-inset-top))" }}
      >
        <button
          type="button"
          onClick={() => setMobileSidebarOpen(true)}
          aria-label="Open sidebar"
          data-testid="mobile-sidebar-toggle"
          className="flex h-11 w-11 shrink-0 items-center justify-center rounded text-lg text-espresso transition hover:bg-cream"
        >
          &#9776;
        </button>
        <span className="truncate text-sm font-semibold text-espresso">Coffee Counter</span>
      </header>
      <div className="flex min-w-0 flex-1 overflow-hidden">
        <Sidebar open={mobileSidebarOpen} onClose={() => setMobileSidebarOpen(false)} />
        <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
          {/* flex-col below lg: CounterDisplay's mobile status bar (see
              SceneShell.tsx) must stack as a full-width block above the
              chat, not sit as a row sibling stealing horizontal space from
              ResponseSection - that was squeezing response-section down to
              ~57% width and stretching the status bar full-height, which is
              what looked like "the barista panel is still visible" on a
              real device. lg:flex-row restores the original side-by-side
              desktop layout, where the mobile status bar is lg:hidden
              anyway and the real scene-shell panel (hidden below lg,
              lg:flex) takes its place on the right. */}
          <div className="flex min-w-0 flex-1 flex-col overflow-hidden lg:flex-row">
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
