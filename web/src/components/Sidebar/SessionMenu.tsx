"use client";

import { useState } from "react";

interface SessionMenuProps {
  onCloseOutSession: () => void;
  onRename: () => void;
  onDelete: () => void;
}

/** Per-session "..." menu (Brew 41, extended Brew 43 with Rename/Delete -
 * docs/design/auth-projects-chat-management-design.md Section 5.2).
 * Delete uses an inline second-click "Confirm delete" state rather than
 * a full-screen dialog - lower friction, consistent with the delete
 * being a soft delete under the hood (Question 4, approved). Stops
 * click propagation so opening the menu (or clicking an item in it)
 * never also selects the session underneath it. */
export function SessionMenu({ onCloseOutSession, onRename, onDelete }: SessionMenuProps) {
  const [open, setOpen] = useState(false);
  const [confirmingDelete, setConfirmingDelete] = useState(false);

  function close() {
    setOpen(false);
    setConfirmingDelete(false);
  }

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
              close();
              onCloseOutSession();
            }}
            data-testid="close-out-session-item"
            className="block w-full px-3 py-2 text-left text-xs text-espresso transition hover:bg-latte"
          >
            Close out this session
          </button>
          <button
            type="button"
            onClick={() => {
              close();
              onRename();
            }}
            data-testid="rename-session-item"
            className="block w-full px-3 py-2 text-left text-xs text-espresso transition hover:bg-latte"
          >
            Rename
          </button>
          {confirmingDelete ? (
            <button
              type="button"
              onClick={() => {
                close();
                onDelete();
              }}
              data-testid="confirm-delete-session-item"
              className="block w-full px-3 py-2 text-left text-xs text-crema-amber transition hover:bg-latte"
            >
              Confirm delete
            </button>
          ) : (
            <button
              type="button"
              onClick={() => setConfirmingDelete(true)}
              data-testid="delete-session-item"
              className="block w-full px-3 py-2 text-left text-xs text-espresso transition hover:bg-latte"
            >
              Delete
            </button>
          )}
        </div>
      )}
    </div>
  );
}
