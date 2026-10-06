"use client";

import { useEffect, useState } from "react";
import * as api from "@/lib/api";

interface FileViewerPanelProps {
  path: string;
  onClose: () => void;
}

/** Read-only overlay panel showing a Pantry source file's raw content
 * (Brew 41, docs/design/memory-and-pantry-design.md Section 4.3) - same
 * `fixed inset-0` overlay pattern as AttachmentGallery's image expand.
 * Fetches from GET /v1/pantry/file, which is path-traversal safe and
 * scoped to knowledge/ only - this panel never assumes that, it just
 * renders whatever the router returns or the error it gives back. */
export function FileViewerPanel({ path, onClose }: FileViewerPanelProps) {
  const [content, setContent] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // No manual state reset here - the parent renders this component with
    // `key={path}` (see PantrySourceChips.tsx), so a new path is a fresh
    // mount with fresh useState defaults rather than a setState-in-effect
    // reset of a reused instance.
    let cancelled = false;
    api
      .getPantryFile(path)
      .then((result) => {
        if (!cancelled) setContent(result.content);
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof Error ? err.message : "Failed to load file.");
      });
    return () => {
      cancelled = true;
    };
  }, [path]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-espresso/80 p-6"
      onClick={onClose}
      data-testid="file-viewer-overlay"
    >
      <div
        className="max-h-[85vh] w-full max-w-3xl overflow-auto rounded bg-cream p-4"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-2 flex items-center justify-between">
          <span className="font-mono text-sm text-espresso">{path}</span>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close file viewer"
            className="rounded border border-caramel px-2 py-1 text-xs text-medium-roast hover:bg-latte"
          >
            Close
          </button>
        </div>
        {error && (
          <p className="text-sm text-crema-amber" data-testid="file-viewer-error">
            {error}
          </p>
        )}
        {!error && content === null && (
          <p className="text-sm text-medium-roast">Loading…</p>
        )}
        {!error && content !== null && (
          <pre className="whitespace-pre-wrap break-words font-mono text-xs text-espresso">{content}</pre>
        )}
      </div>
    </div>
  );
}
