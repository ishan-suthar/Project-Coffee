"use client";

import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { useChatStore } from "@/store/chatStore";
import * as api from "@/lib/api";
import type { Bean } from "@/lib/events";
import type { AttachmentSummary } from "@/lib/chat";
import { ACCEPT_ATTRIBUTE, AttachmentKind, validateFileClientSide } from "@/lib/attachments";
import { v4 as uuidv4 } from "@/lib/uuid";
import { AttachmentChip, AttachmentChipStatus } from "@/components/OrderBox/AttachmentChip";

/** Title Case for a snake_case complexity value ("espresso_shot" -> "Espresso Shot"). */
function titleCase(value: string): string {
  return value
    .split("_")
    .map((word) => word[0].toUpperCase() + word.slice(1))
    .join(" ");
}

// ~5 lines at the textarea's 16px/1.5 line-height, plus vertical padding -
// beyond this the textarea scrolls internally instead of growing further.
const TEXTAREA_MAX_HEIGHT_PX = 136;

interface AttachmentChipState {
  clientId: string;
  attachmentId: string | null;
  file: File;
  status: AttachmentChipStatus;
  errorMessage: string | null;
  kind: AttachmentKind | null;
  previewUrl: string | null;
}

export function OrderBox() {
  const [prompt, setPrompt] = useState("");
  const [overrideAlias, setOverrideAlias] = useState("");
  const [usePantry, setUsePantry] = useState(false);
  const [useWeb, setUseWeb] = useState(false);
  const [beans, setBeans] = useState<Bean[]>([]);
  const [attachments, setAttachments] = useState<AttachmentChipState[]>([]);
  const [draftRequestId, setDraftRequestId] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const attachmentsRef = useRef(attachments);
  const sendPrompt = useChatStore((s) => s.sendPrompt);
  const cancelActive = useChatStore((s) => s.cancelActive);
  const activeRequestId = useChatStore((s) => s.activeRequestId);
  const latestRouteEvent = useChatStore((s) => {
    const messages = s.activeSessionId ? s.messages[s.activeSessionId] ?? [] : [];
    const last = messages[messages.length - 1];
    return last?.latestEvent?.event === "route_selected" ? last.latestEvent : null;
  });

  useEffect(() => {
    api.listBeans().then(setBeans).catch(() => setBeans([]));
  }, []);

  // Auto-grow the textarea with content, up to TEXTAREA_MAX_HEIGHT_PX, then
  // it scrolls internally - reset to "auto" first so shrinking (e.g. after
  // send clears the prompt) is measured correctly, not just growth.
  useLayoutEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, TEXTAREA_MAX_HEIGHT_PX)}px`;
  }, [prompt]);

  useEffect(() => {
    attachmentsRef.current = attachments;
  }, [attachments]);

  useEffect(() => {
    // Revoke any still-outstanding preview blob URLs (attached but never
    // sent) so we don't leak them past this component's lifetime.
    return () => {
      for (const attachment of attachmentsRef.current) {
        if (attachment.previewUrl) URL.revokeObjectURL(attachment.previewUrl);
      }
    };
  }, []);

  useEffect(() => {
    function handleEsc(event: KeyboardEvent) {
      if (event.key === "Escape" && activeRequestId !== null) {
        cancelActive();
      }
    }
    window.addEventListener("keydown", handleEsc);
    return () => window.removeEventListener("keydown", handleEsc);
  }, [activeRequestId, cancelActive]);

  function addFiles(files: File[]) {
    if (files.length === 0) return;
    const requestId = draftRequestId ?? uuidv4();
    if (draftRequestId === null) setDraftRequestId(requestId);

    for (const file of files) {
      const clientId = uuidv4();
      const validation = validateFileClientSide(file);
      if (!validation.valid) {
        setAttachments((prev) => [
          ...prev,
          {
            clientId,
            attachmentId: null,
            file,
            status: "error",
            errorMessage: validation.error,
            kind: null,
            previewUrl: null,
          },
        ]);
        continue;
      }

      const previewUrl = file.type.startsWith("image/") ? URL.createObjectURL(file) : null;
      setAttachments((prev) => [
        ...prev,
        { clientId, attachmentId: null, file, status: "pending", errorMessage: null, kind: null, previewUrl },
      ]);

      api
        .uploadFile(requestId, file)
        .then((response) => {
          setAttachments((prev) =>
            prev.map((a) =>
              a.clientId === clientId
                ? { ...a, attachmentId: response.attachment_id, status: "ready", kind: response.kind }
                : a
            )
          );
        })
        .catch((err: unknown) => {
          setAttachments((prev) =>
            prev.map((a) =>
              a.clientId === clientId
                ? { ...a, status: "error", errorMessage: err instanceof Error ? err.message : "Upload failed." }
                : a
            )
          );
        });
    }
  }

  function removeAttachment(clientId: string) {
    setAttachments((prev) => {
      const target = prev.find((a) => a.clientId === clientId);
      if (target?.previewUrl) URL.revokeObjectURL(target.previewUrl);
      return prev.filter((a) => a.clientId !== clientId);
    });
  }

  const hasPendingUpload = attachments.some((a) => a.status === "pending");

  async function handleSend() {
    const trimmed = prompt.trim();
    if ((trimmed.length === 0 && attachments.length === 0) || activeRequestId !== null || hasPendingUpload) {
      return;
    }

    const readyAttachments = attachments.filter((a) => a.status === "ready" && a.attachmentId !== null);
    const attachmentIds = readyAttachments.map((a) => a.attachmentId as string);
    const attachmentSummaries: AttachmentSummary[] = readyAttachments.map((a) => ({
      attachmentId: a.attachmentId as string,
      filename: a.file.name,
      sizeBytes: a.file.size,
      kind: a.kind as AttachmentKind,
      previewUrl: a.previewUrl,
    }));
    const requestId = draftRequestId ?? undefined;

    setPrompt("");
    setAttachments([]);
    setDraftRequestId(null);
    await sendPrompt(trimmed, {
      beanAliasOverride: overrideAlias || undefined,
      attachmentIds,
      attachments: attachmentSummaries,
      requestId,
      usePantry,
      useWeb,
    });
  }

  function handleKeyDown(event: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      handleSend();
    }
    // Shift+Enter: default textarea behavior inserts a newline - no
    // handling needed here.
  }

  function handlePaste(event: React.ClipboardEvent<HTMLTextAreaElement>) {
    const items = event.clipboardData?.items;
    if (!items) return;
    const imageFiles: File[] = [];
    for (const item of Array.from(items)) {
      if (item.kind === "file" && item.type.startsWith("image/")) {
        const file = item.getAsFile();
        if (file) imageFiles.push(file);
      }
    }
    if (imageFiles.length > 0) addFiles(imageFiles);
  }

  function handleDragOver(event: React.DragEvent<HTMLDivElement>) {
    event.preventDefault();
  }

  function handleDrop(event: React.DragEvent<HTMLDivElement>) {
    event.preventDefault();
    addFiles(Array.from(event.dataTransfer.files));
  }

  return (
    <div
      className="shrink-0 border-t border-caramel bg-latte p-3 shadow-inner"
      style={{ paddingBottom: "calc(0.75rem + env(safe-area-inset-bottom))" }}
      data-testid="order-box"
      onDragOver={handleDragOver}
      onDrop={handleDrop}
    >
      {latestRouteEvent && (
        <p className="mb-1 text-xs text-medium-roast" data-testid="routing-hint">
          {titleCase(latestRouteEvent.complexity)}, {latestRouteEvent.bean_alias}
          {latestRouteEvent.constraint_reason && ` (${latestRouteEvent.constraint_reason})`}
        </p>
      )}

      {attachments.length > 0 && (
        <div className="mb-2 flex flex-wrap gap-2" data-testid="attachment-chip-row">
          {attachments.map((a) => (
            <AttachmentChip
              key={a.clientId}
              filename={a.file.name}
              sizeBytes={a.file.size}
              status={a.status}
              errorMessage={a.errorMessage}
              previewUrl={a.previewUrl}
              onRemove={() => removeAttachment(a.clientId)}
            />
          ))}
        </div>
      )}

      {/* Compact controls row, sits above the textarea/send row so Send
          never gets pushed out of reach by an unpredictable number of
          toggles. Grouped into two nowrap sub-rows (attach+route, then the
          two toggles together) so flex-wrap on the outer row only ever
          breaks BETWEEN groups - at 390px this previously wrapped per
          item, orphaning "Use Web" alone on its own line once
          attach+route+Pantry filled line 1; now Pantry and Web always wrap
          together as a pair, never separated. */}
      <div className="mb-2 flex flex-wrap items-center gap-x-3 gap-y-2">
        <div className="flex shrink-0 items-center gap-2">
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept={ACCEPT_ATTRIBUTE}
            onChange={(e) => {
              addFiles(Array.from(e.target.files ?? []));
              e.target.value = "";
            }}
            className="hidden"
            data-testid="attachment-file-input"
          />
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            aria-label="Attach a file"
            data-testid="attachment-paperclip-button"
            className="flex h-11 w-11 shrink-0 items-center justify-center rounded border border-caramel text-base text-medium-roast transition hover:bg-cream"
          >
            📎
          </button>

          <select
            aria-label="Manual Bean override"
            data-testid="bean-override-select"
            value={overrideAlias}
            onChange={(e) => setOverrideAlias(e.target.value)}
            className="h-11 rounded border border-caramel bg-cream px-2 font-mono text-base text-espresso"
          >
            <option value="">Auto route</option>
            {beans
              .filter((bean) => bean.available)
              .map((bean) => (
                <option key={bean.alias} value={bean.alias}>
                  {bean.alias}
                </option>
              ))}
          </select>
        </div>

        <div className="flex shrink-0 items-center gap-3">
          <label
            className="flex min-h-11 items-center gap-1.5 whitespace-nowrap text-xs text-medium-roast"
            title="Prepend relevant knowledge/ excerpts to this request, with citations"
          >
            <input
              type="checkbox"
              data-testid="use-pantry-toggle"
              checked={usePantry}
              onChange={(e) => setUsePantry(e.target.checked)}
              className="h-5 w-5"
            />
            Use Pantry
          </label>

          <label
            className="flex min-h-11 items-center gap-1.5 whitespace-nowrap text-xs text-medium-roast"
            title="Search the web for this request - always leaves the free tier (routes to a tool-calling-capable Bean)"
          >
            <input
              type="checkbox"
              data-testid="use-web-toggle"
              checked={useWeb}
              onChange={(e) => setUseWeb(e.target.checked)}
              className="h-5 w-5"
            />
            Use Web
          </label>
        </div>
      </div>

      {/* Textarea + send row - kept together so Send is always reachable
          right next to where the user is typing, matching Claude/ChatGPT
          mobile composer layout. */}
      <div className="flex items-end gap-2">
        <textarea
          ref={textareaRef}
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          onKeyDown={handleKeyDown}
          onPaste={handlePaste}
          placeholder="Place your order... (Enter to send, Shift+Enter for a newline)"
          rows={1}
          disabled={activeRequestId !== null}
          style={{ maxHeight: TEXTAREA_MAX_HEIGHT_PX }}
          className="min-w-0 flex-1 resize-none overflow-y-auto rounded border border-caramel bg-cream px-3 py-2.5 text-base text-espresso outline-none focus:border-crema-amber"
        />

        {activeRequestId !== null ? (
          <button
            type="button"
            onClick={cancelActive}
            title="Cancel (Esc)"
            className="flex h-11 shrink-0 items-center justify-center rounded border border-crema-amber px-3 text-sm text-crema-amber transition hover:bg-cream"
          >
            Cancel
          </button>
        ) : (
          <button
            type="button"
            onClick={handleSend}
            disabled={(prompt.trim().length === 0 && attachments.length === 0) || hasPendingUpload}
            title="Send"
            className="flex h-11 shrink-0 items-center justify-center rounded bg-crema-amber px-4 text-sm text-cream transition hover:opacity-90 disabled:opacity-50"
          >
            Send
          </button>
        )}
      </div>
    </div>
  );
}
