"use client";

import { useState } from "react";
import type { AttachmentSummary } from "@/lib/chat";
import { formatFileSize } from "@/lib/attachments";

interface AttachmentGalleryProps {
  attachments: AttachmentSummary[];
}

/** Read-only rendering of a sent message's attachments: images inline at
 * a constrained size with click-to-expand, non-image attachments as a
 * plain chip (filename + size). See docs/design/attachments-design.md
 * Section 10. */
export function AttachmentGallery({ attachments }: AttachmentGalleryProps) {
  const [expandedUrl, setExpandedUrl] = useState<string | null>(null);

  if (attachments.length === 0) return null;

  return (
    <div className="mb-2 flex flex-wrap gap-2" data-testid="attachment-gallery">
      {attachments.map((attachment) =>
        attachment.kind === "image" && attachment.previewUrl ? (
          <img
            key={attachment.attachmentId}
            src={attachment.previewUrl}
            alt={attachment.filename}
            className="max-h-64 cursor-pointer rounded object-cover"
            onClick={() => setExpandedUrl(attachment.previewUrl)}
            data-testid="attachment-gallery-image"
          />
        ) : (
          <div
            key={attachment.attachmentId}
            className="flex items-center gap-2 rounded border border-caramel bg-latte px-2 py-1 text-xs text-espresso"
            data-testid="attachment-gallery-chip"
          >
            <span className="max-w-[10rem] truncate" title={attachment.filename}>
              {attachment.filename}
            </span>
            <span className="text-medium-roast">{formatFileSize(attachment.sizeBytes)}</span>
          </div>
        )
      )}

      {expandedUrl && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-espresso/80"
          onClick={() => setExpandedUrl(null)}
          data-testid="attachment-gallery-overlay"
        >
          <img src={expandedUrl} alt="" className="max-h-[90vh] max-w-[90vw] rounded" />
        </div>
      )}
    </div>
  );
}
