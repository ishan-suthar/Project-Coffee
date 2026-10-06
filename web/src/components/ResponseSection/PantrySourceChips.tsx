"use client";

import { useState } from "react";
import { FileViewerPanel } from "@/components/ResponseSection/FileViewerPanel";

interface PantrySourceChipsProps {
  sources: string[] | null;
}

/** Citation chips for the Pantry sources the router actually injected
 * into a request (Brew 41, contract v1.4 pantry_sources) - renders only
 * from `sources`, which is only ever non-null/non-empty when the router
 * itself reported real injected sources, so a chip can never claim a
 * source that wasn't used (Constitution Article 6.4 / Requirement 7).
 * Clicking a chip opens a read-only FileViewerPanel. */
export function PantrySourceChips({ sources }: PantrySourceChipsProps) {
  const [openPath, setOpenPath] = useState<string | null>(null);

  if (!sources || sources.length === 0) return null;

  return (
    <>
      <div className="mt-2 flex flex-wrap gap-2" data-testid="pantry-source-chips">
        {sources.map((path) => (
          <button
            key={path}
            type="button"
            onClick={() => setOpenPath(path)}
            className="rounded border border-caramel bg-latte px-2 py-1 font-mono text-xs text-medium-roast transition hover:bg-cream"
            data-testid="pantry-source-chip"
          >
            {path}
          </button>
        ))}
      </div>
      {openPath && (
        <FileViewerPanel key={openPath} path={openPath} onClose={() => setOpenPath(null)} />
      )}
    </>
  );
}
