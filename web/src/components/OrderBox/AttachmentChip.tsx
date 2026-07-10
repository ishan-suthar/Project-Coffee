import { formatFileSize } from "@/lib/attachments";

export type AttachmentChipStatus = "pending" | "ready" | "error";

interface AttachmentChipProps {
  filename: string;
  sizeBytes: number;
  status: AttachmentChipStatus;
  errorMessage?: string | null;
  previewUrl?: string | null;
  onRemove: () => void;
}

/** One chip in the Order Box's attachment row. Always removable, even in
 * `error` state (per docs/design/attachments-design.md Section 9.1's chip
 * state table). */
export function AttachmentChip({
  filename,
  sizeBytes,
  status,
  errorMessage,
  previewUrl,
  onRemove,
}: AttachmentChipProps) {
  return (
    <div
      className="flex items-center gap-2 rounded border border-caramel bg-cream px-2 py-1 text-xs text-espresso"
      data-testid="attachment-chip"
      data-status={status}
    >
      {previewUrl && (
        <img src={previewUrl} alt="" className="h-6 w-6 rounded object-cover" data-testid="attachment-chip-thumbnail" />
      )}
      <span className="max-w-[10rem] truncate" data-testid="attachment-chip-filename" title={filename}>
        {filename}
      </span>
      <span className="text-medium-roast">{formatFileSize(sizeBytes)}</span>
      {status === "pending" && (
        <span className="text-medium-roast" data-testid="attachment-chip-pending">
          uploading…
        </span>
      )}
      {status === "error" && (
        <span className="text-crema-amber" data-testid="attachment-chip-error">
          {errorMessage}
        </span>
      )}
      <button
        type="button"
        onClick={onRemove}
        aria-label={`Remove ${filename}`}
        data-testid="attachment-chip-remove"
        className="text-medium-roast hover:text-espresso"
      >
        ×
      </button>
    </div>
  );
}
