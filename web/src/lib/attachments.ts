/**
 * File/image attachment client-side helpers (Brew 38). Mirrors
 * router/app/uploads.py's allowlist and router/config/settings.yaml's
 * max_upload_size_bytes default. This is a pre-check for instant feedback
 * only - the router's own validate_upload() is authoritative and is
 * never bypassed by this.
 */

export type AttachmentKind = "image" | "pdf" | "text";

const IMAGE_EXTENSIONS = [".png", ".jpg", ".jpeg", ".webp"];
const PDF_EXTENSIONS = [".pdf"];
const TEXT_EXTENSIONS = [".md", ".txt", ".csv", ".py", ".r", ".sas", ".json"];

export const ALLOWED_EXTENSIONS = [...IMAGE_EXTENSIONS, ...PDF_EXTENSIONS, ...TEXT_EXTENSIONS];
export const ACCEPT_ATTRIBUTE = ALLOWED_EXTENSIONS.join(",");

export const MAX_UPLOAD_SIZE_BYTES = 20 * 1024 * 1024; // matches settings.yaml default

export interface UploadResponse {
  attachment_id: string;
  filename: string;
  content_type: string;
  kind: AttachmentKind;
  size_bytes: number;
  extracted_text_chars: number | null;
}

export interface ClientValidationResult {
  valid: boolean;
  error: string | null;
}

export function validateFileClientSide(file: File): ClientValidationResult {
  const extension = extensionOf(file.name);
  if (!ALLOWED_EXTENSIONS.includes(extension)) {
    return { valid: false, error: `${extension || "(no extension)"} is not an allowed file type.` };
  }
  if (file.size > MAX_UPLOAD_SIZE_BYTES) {
    return {
      valid: false,
      error: `File is too large (${formatFileSize(file.size)}, max ${formatFileSize(MAX_UPLOAD_SIZE_BYTES)}).`,
    };
  }
  return { valid: true, error: null };
}

export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  const units = ["KB", "MB", "GB"];
  let value = bytes / 1024;
  let unitIndex = 0;
  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024;
    unitIndex += 1;
  }
  return `${value.toFixed(value < 10 ? 1 : 0)} ${units[unitIndex]}`;
}

function extensionOf(filename: string): string {
  const dotIndex = filename.lastIndexOf(".");
  return dotIndex === -1 ? "" : filename.slice(dotIndex).toLowerCase();
}
