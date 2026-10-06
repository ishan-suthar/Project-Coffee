"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useChatStore } from "@/store/chatStore";
import { formatRelativeTime } from "@/lib/relativeTime";
import { SessionMenu } from "@/components/Sidebar/SessionMenu";
import { ProjectSelector } from "@/components/Sidebar/ProjectSelector";
import { MemoryProposalPanel } from "@/components/MemoryProposal/MemoryProposalPanel";
import { SettingsPanel } from "@/components/Settings/SettingsPanel";
import * as api from "@/lib/api";
import { getStoredUser } from "@/lib/authFetch";

interface SidebarProps {
  /** Mobile-only (<768px) slide-over drawer state, owned by page.tsx.
   * Ignored at md and up (Tailwind's md: overrides put Sidebar back in
   * its normal static, in-flow position there, unaffected by this prop) -
   * both default to inert values so every existing call site/test that
   * renders <Sidebar /> with no props keeps working unchanged. */
  open?: boolean;
  onClose?: () => void;
}

/**
 * Sessions grouped by project, collapsible to an icon rail. Fetched AFTER
 * interactive (Requirement: first paint never blocked) - this component
 * renders an empty/skeleton list immediately and populates it via
 * useEffect, matching docs/design/coffee-counter-chat-ui-design.md
 * Section 5.1. Collapse state is a UI preference (localStorage), not
 * session data.
 */
export function Sidebar({ open = false, onClose }: SidebarProps = {}) {
  const router = useRouter();
  const [collapsed, setCollapsed] = useState(false);
  const [closeOutSessionId, setCloseOutSessionId] = useState<string | null>(null);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [renamingSessionId, setRenamingSessionId] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState("");
  const [displayName, setDisplayName] = useState<string | null>(null);
  const sessions = useChatStore((s) => s.sessions);
  const sessionsLoaded = useChatStore((s) => s.sessionsLoaded);
  const activeSessionId = useChatStore((s) => s.activeSessionId);
  const loadSessions = useChatStore((s) => s.loadSessions);
  const selectSession = useChatStore((s) => s.selectSession);
  const startNewSession = useChatStore((s) => s.startNewSession);
  const renameSession = useChatStore((s) => s.renameSession);
  const deleteSession = useChatStore((s) => s.deleteSession);

  useEffect(() => {
    // One-shot read of a UI preference on mount, not a synchronization
    // loop - localStorage is unavailable during SSR, so this cannot be a
    // useState lazy initializer without a hydration mismatch.
    const stored = window.localStorage.getItem("coffee-counter-sidebar-collapsed");
    // eslint-disable-next-line react-hooks/set-state-in-effect
    if (stored === "true") setCollapsed(true);
    setDisplayName(getStoredUser()?.display_name ?? null);
  }, []);

  useEffect(() => {
    loadSessions().catch(() => {
      // Sidebar failing to load must never block the shell or the order
      // box - it just stays empty and the user can still start a chat.
    });
  }, [loadSessions]);

  function toggleCollapsed() {
    setCollapsed((prev) => {
      const next = !prev;
      window.localStorage.setItem("coffee-counter-sidebar-collapsed", String(next));
      return next;
    });
  }

  async function handleSignOut() {
    await api.logout();
    router.push("/login");
  }

  function startRename(sessionId: string, currentTitle: string) {
    setRenamingSessionId(sessionId);
    setRenameValue(currentTitle);
  }

  function commitRename() {
    if (renamingSessionId === null) return;
    const title = renameValue.trim();
    if (title.length > 0) renameSession(renamingSessionId, title);
    setRenamingSessionId(null);
  }

  // Mobile-only (<768px) slide-over drawer mechanics, applied identically
  // to both the collapsed-rail and full-sidebar variants below via
  // responsive classes that go inert at md and up (md:static/md:z-auto/
  // md:translate-x-0 restore the exact pre-existing static/in-flow
  // positioning there - see docs comment on SidebarProps). The backdrop
  // is the "tap outside to close" affordance; only rendered at all when
  // open, and hidden again at md via md:hidden since the drawer itself
  // has no mobile-only positioning to escape from there.
  const mobileDrawerClasses = `fixed inset-y-0 left-0 z-40 transition-transform duration-200 md:static md:z-auto md:translate-x-0 md:transition-none ${
    open ? "translate-x-0" : "-translate-x-full"
  }`;
  const backdrop = open && (
    <div
      className="fixed inset-0 z-30 bg-espresso/40 md:hidden"
      onClick={onClose}
      aria-hidden="true"
      data-testid="sidebar-mobile-overlay"
    />
  );

  if (collapsed) {
    return (
      <>
        {backdrop}
        <div className={`flex w-12 flex-col items-center border-r border-caramel bg-latte py-2 ${mobileDrawerClasses}`}>
          <button
            type="button"
            onClick={toggleCollapsed}
            aria-label="Expand sidebar"
            className="rounded px-2 py-1 text-espresso transition hover:bg-cream"
          >
            &rarr;
          </button>
        </div>
      </>
    );
  }

  return (
    <>
      {backdrop}
      <aside className={`flex w-64 flex-col border-r border-caramel bg-latte ${mobileDrawerClasses}`}>
      <div className="flex items-center justify-between border-b border-caramel px-3 py-2">
        <ProjectSelector />
        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={() => setSettingsOpen(true)}
            aria-label="Open settings"
            data-testid="open-settings-button"
            className="rounded px-2 py-1 text-espresso transition hover:bg-cream"
          >
            &#9881;
          </button>
          <button
            type="button"
            onClick={toggleCollapsed}
            aria-label="Collapse sidebar"
            className="rounded px-2 py-1 text-espresso transition hover:bg-cream"
          >
            &larr;
          </button>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close sidebar"
            data-testid="sidebar-mobile-close"
            className="rounded px-2 py-1 text-espresso transition hover:bg-cream md:hidden"
          >
            &#10005;
          </button>
        </div>
      </div>

      <button
        type="button"
        onClick={() => {
          startNewSession();
          onClose?.();
        }}
        className="m-2 rounded border border-caramel px-3 py-2 text-left text-sm text-espresso transition hover:bg-cream"
      >
        + New session
      </button>

      <div className="flex-1 overflow-y-auto px-2 pb-2" data-testid="sidebar-sessions">
        {!sessionsLoaded && <p className="px-2 text-xs text-medium-roast">Loading sessions...</p>}
        {sessionsLoaded && sessions.length === 0 && (
          <p className="px-2 text-xs text-medium-roast">No sessions yet.</p>
        )}
        {sessions.map((session) => (
          <div
            key={session.id}
            className={`mb-1 flex items-center rounded transition ${
              session.id === activeSessionId ? "bg-crema-amber/20" : "hover:bg-cream"
            }`}
          >
            {renamingSessionId === session.id ? (
              <input
                autoFocus
                value={renameValue}
                onChange={(e) => setRenameValue(e.target.value)}
                onBlur={commitRename}
                onKeyDown={(e) => {
                  if (e.key === "Enter") commitRename();
                  if (e.key === "Escape") setRenamingSessionId(null);
                }}
                data-testid="session-rename-input"
                className="min-w-0 flex-1 rounded border border-caramel bg-cream px-2 py-2 text-sm text-espresso outline-none"
              />
            ) : (
              <button
                type="button"
                onClick={() => {
                  selectSession(session.id);
                  onClose?.();
                }}
                className="flex min-w-0 flex-1 flex-col px-2 py-2 text-left"
              >
                <span className="truncate text-sm text-espresso">{session.title}</span>
                <span className="flex items-center justify-between text-xs text-medium-roast">
                  <span>{formatRelativeTime(session.updated_at)}</span>
                  <span className="font-mono tabular-nums">${session.cost_total_usd.toFixed(4)}</span>
                </span>
              </button>
            )}
            <SessionMenu
              onCloseOutSession={() => setCloseOutSessionId(session.id)}
              onRename={() => startRename(session.id, session.title)}
              onDelete={() => deleteSession(session.id)}
            />
          </div>
        ))}
      </div>

      <div className="flex items-center justify-between border-t border-caramel px-3 py-2">
        <span className="truncate text-xs text-medium-roast" data-testid="signed-in-as">
          {displayName ?? ""}
        </span>
        <button
          type="button"
          onClick={handleSignOut}
          data-testid="sign-out-button"
          className="rounded border border-caramel px-2 py-1 text-xs text-medium-roast transition hover:bg-cream"
        >
          Sign out
        </button>
      </div>

      {closeOutSessionId && (
        <MemoryProposalPanel
          sessionId={closeOutSessionId}
          onClose={() => setCloseOutSessionId(null)}
        />
      )}
      {settingsOpen && <SettingsPanel onClose={() => setSettingsOpen(false)} />}
      </aside>
    </>
  );
}
