"use client";

import { useEffect, useState } from "react";
import { useChatStore } from "@/store/chatStore";

/**
 * Ctrl+K command palette stub - session jump only for now, per
 * docs/design/coffee-counter-chat-ui-design.md. Not a full command
 * system yet; that is future work.
 */
export function CommandPalette() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const sessions = useChatStore((s) => s.sessions);
  const selectSession = useChatStore((s) => s.selectSession);

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if ((event.metaKey || event.ctrlKey) && event.key === "k") {
        event.preventDefault();
        setOpen((prev) => !prev);
      }
      if (event.key === "Escape") {
        setOpen(false);
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  if (!open) return null;

  const filtered = sessions.filter((s) => s.title.toLowerCase().includes(query.toLowerCase()));

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center bg-espresso/40 pt-24"
      onClick={() => setOpen(false)}
      data-testid="command-palette"
    >
      <div
        className="w-full max-w-md rounded-lg border border-caramel bg-cream shadow-lg"
        onClick={(e) => e.stopPropagation()}
      >
        <input
          autoFocus
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Jump to session..."
          className="w-full border-b border-caramel bg-transparent px-4 py-3 text-sm text-espresso outline-none"
        />
        <ul className="max-h-64 overflow-y-auto">
          {filtered.map((session) => (
            <li key={session.id}>
              <button
                type="button"
                onClick={() => {
                  selectSession(session.id);
                  setOpen(false);
                  setQuery("");
                }}
                className="block w-full px-4 py-2 text-left text-sm text-espresso transition hover:bg-latte"
              >
                {session.title}
              </button>
            </li>
          ))}
          {filtered.length === 0 && (
            <li className="px-4 py-2 text-sm text-medium-roast">No matching sessions.</li>
          )}
        </ul>
      </div>
    </div>
  );
}
