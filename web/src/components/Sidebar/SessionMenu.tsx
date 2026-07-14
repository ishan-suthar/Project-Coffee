"use client";

import { useState } from "react";

interface SessionMenuProps {
  onCloseOutSession: () => void;
}

/** Per-session "..." menu (Brew 41) - the first per-session action of its
 * kind, so this is a new small affordance rather than an extension of
 * the existing plain session button (docs/design/
 * memory-and-pantry-design.md Section 2, Gap 3). Stops click propagation
 * so opening the menu (or clicking an item in it) never also selects the
 * session underneath it. */
export function SessionMenu({ onCloseOutSession }: SessionMenuProps) {
  const [open, setOpen] = useState(false);

  return (
    <div className="relative" onClick={(e) => e.stopPropagation()}>
      <button
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        aria-label="Session actions"
        data-testid="session-menu-button"
        className="rounded px-2 py-1 text-medium-roast transition hover:bg-cream"
      >
        &#8942;
      </button>
      {open && (
        <div
          className="absolute right-0 top-full z-10 mt-1 w-48 rounded border border-caramel bg-cream shadow-md"
          data-testid="session-menu-dropdown"
        >
          <button
            type="button"
            onClick={() => {
              setOpen(false);
              onCloseOutSession();
            }}
            data-testid="close-out-session-item"
            className="block w-full px-3 py-2 text-left text-xs text-espresso transition hover:bg-latte"
          >
            Close out this session
          </button>
        </div>
      )}
    </div>
  );
}
