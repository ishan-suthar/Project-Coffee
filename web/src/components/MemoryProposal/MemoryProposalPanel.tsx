"use client";

import { useEffect, useState } from "react";
import * as api from "@/lib/api";
import type { MemoryProposalFile } from "@/lib/api";
import { DiffView } from "@/components/Settings/DiffView";

interface MemoryProposalPanelProps {
  sessionId: string;
  onClose: () => void;
}

type Status = "loading" | "ready" | "error" | "submitting";

/** Brew 41 (docs/design/memory-and-pantry-design.md Section 3): generates
 * a memory proposal for `sessionId` on mount and lets a human review the
 * diff before it ever touches disk - approve writes both files via
 * POST .../approve, discard just drops the in-memory proposal. Nothing
 * is written to brew-log/ without an explicit click here. */
export function MemoryProposalPanel({ sessionId, onClose }: MemoryProposalPanelProps) {
  const [status, setStatus] = useState<Status>("loading");
  const [proposalId, setProposalId] = useState<string | null>(null);
  const [files, setFiles] = useState<MemoryProposalFile[]>([]);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .generateMemoryProposal(sessionId)
      .then((result) => {
        if (cancelled) return;
        setProposalId(result.proposal_id);
        setFiles(result.files);
        setStatus("ready");
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setErrorMessage(err instanceof Error ? err.message : "Failed to generate proposal.");
        setStatus("error");
      });
    return () => {
      cancelled = true;
    };
  }, [sessionId]);

  async function handleApprove() {
    if (proposalId === null) return;
    setStatus("submitting");
    try {
      await api.approveMemoryProposal(proposalId);
      onClose();
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : "Failed to approve proposal.");
      setStatus("ready");
    }
  }

  async function handleDiscard() {
    if (proposalId === null) {
      onClose();
      return;
    }
    setStatus("submitting");
    try {
      await api.discardMemoryProposal(proposalId);
    } finally {
      onClose();
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-espresso/80 p-6"
      data-testid="memory-proposal-overlay"
    >
      <div className="max-h-[85vh] w-full max-w-2xl overflow-auto rounded bg-cream p-4">
        <div className="mb-3 flex items-center justify-between">
          <span className="text-sm font-medium text-espresso">Close out this session</span>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close proposal panel"
            className="rounded border border-caramel px-2 py-1 text-xs text-medium-roast hover:bg-latte"
          >
            Close
          </button>
        </div>

        {status === "loading" && (
          <p className="text-sm text-medium-roast" data-testid="memory-proposal-loading">
            Drafting a memory proposal…
          </p>
        )}

        {status === "error" && (
          <p className="text-sm text-crema-amber" data-testid="memory-proposal-error">
            {errorMessage}
          </p>
        )}

        {(status === "ready" || status === "submitting") && (
          <>
            {files.map((file) => (
              <div key={file.path} className="mb-4">
                <p className="mb-1 font-mono text-xs text-espresso">{file.path}</p>
                <DiffView diff={file.diff} emptyMessage="No changes proposed for this file." />
              </div>
            ))}
            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={handleDiscard}
                disabled={status === "submitting"}
                data-testid="memory-proposal-discard"
                className="rounded border border-caramel px-3 py-2 text-sm text-medium-roast transition hover:bg-latte disabled:opacity-50"
              >
                Discard
              </button>
              <button
                type="button"
                onClick={handleApprove}
                disabled={status === "submitting"}
                data-testid="memory-proposal-approve"
                className="rounded bg-crema-amber px-3 py-2 text-sm text-cream transition hover:opacity-90 disabled:opacity-50"
              >
                Approve
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
