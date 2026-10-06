"use client";

import { useState } from "react";
import * as api from "@/lib/api";
import { DiffView } from "@/components/Settings/DiffView";

interface SettingsPanelProps {
  onClose: () => void;
}

type Status = "idle" | "loading" | "ready" | "error" | "submitting" | "applied";

/** Brew 42 (docs/design/learning-loop-and-release-design.md Section 3.2):
 * the first settings-shaped UI surface in this app. Today it has one
 * section - "Rebuild House Blend" - which previews a routing_policy.yaml
 * rebuild (blending Roastery Cup Test evidence with real accumulated
 * ratings) as a diff, and any task_types with a real escalation rate
 * above settings.escalation_rate_flag_threshold are surfaced as
 * advisory-only warnings above it. Never hot-swaps policy without
 * showing this diff for approval first. */
export function SettingsPanel({ onClose }: SettingsPanelProps) {
  const [status, setStatus] = useState<Status>("idle");
  const [proposalId, setProposalId] = useState<string | null>(null);
  const [diff, setDiff] = useState("");
  const [escalationCandidates, setEscalationCandidates] = useState<string[]>([]);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  async function handleRebuild() {
    setStatus("loading");
    setErrorMessage(null);
    try {
      const result = await api.rebuildPolicyPreview();
      setProposalId(result.proposal_id);
      setDiff(result.diff);
      setEscalationCandidates(result.escalation_candidates);
      setStatus("ready");
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : "Failed to preview a policy rebuild.");
      setStatus("error");
    }
  }

  async function handleApprove() {
    if (proposalId === null) return;
    setStatus("submitting");
    try {
      await api.rebuildPolicyApply(proposalId);
      setStatus("applied");
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : "Failed to apply the policy rebuild.");
      setStatus("ready");
    }
  }

  async function handleDiscard() {
    if (proposalId === null) return;
    setStatus("submitting");
    try {
      await api.rebuildPolicyDiscard(proposalId);
    } finally {
      setProposalId(null);
      setDiff("");
      setEscalationCandidates([]);
      setStatus("idle");
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-espresso/80 p-6"
      data-testid="settings-panel-overlay"
    >
      <div className="max-h-[85vh] w-full max-w-2xl overflow-auto rounded bg-cream p-4">
        <div className="mb-3 flex items-center justify-between">
          <span className="text-sm font-medium text-espresso">Settings</span>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close settings"
            className="rounded border border-caramel px-2 py-1 text-xs text-medium-roast hover:bg-latte"
          >
            Close
          </button>
        </div>

        <div className="mb-2">
          <h3 className="text-sm font-medium text-espresso">Routing Policy</h3>
          <p className="text-xs text-medium-roast">
            Rebuild router/config/routing_policy.yaml from Roastery Cup Test evidence and real
            accumulated ratings. Nothing changes until you approve the diff below.
          </p>
        </div>

        {status === "idle" && (
          <button
            type="button"
            onClick={handleRebuild}
            data-testid="rebuild-house-blend-button"
            className="rounded bg-crema-amber px-3 py-2 text-sm text-cream transition hover:opacity-90"
          >
            Rebuild House Blend
          </button>
        )}

        {status === "loading" && (
          <p className="text-sm text-medium-roast" data-testid="settings-loading">
            Computing a policy rebuild preview…
          </p>
        )}

        {status === "error" && (
          <p className="text-sm text-crema-amber" data-testid="settings-error">
            {errorMessage}
          </p>
        )}

        {status === "applied" && (
          <p className="text-sm text-espresso" data-testid="settings-applied">
            Applied - routing_policy.yaml was updated and is in effect immediately, no restart
            needed.
          </p>
        )}

        {(status === "ready" || status === "submitting") && (
          <>
            {escalationCandidates.length > 0 && (
              <p
                className="mb-2 rounded border border-crema-amber bg-crema-amber/10 p-2 text-xs text-espresso"
                data-testid="escalation-candidates-warning"
              >
                Escalation-rate candidates (advisory only, routing is unchanged): {escalationCandidates.join(", ")}
              </p>
            )}
            <DiffView diff={diff} emptyMessage="No changes proposed - routing policy is already up to date." />
            <div className="mt-2 flex justify-end gap-2">
              <button
                type="button"
                onClick={handleDiscard}
                disabled={status === "submitting"}
                data-testid="settings-discard"
                className="rounded border border-caramel px-3 py-2 text-sm text-medium-roast transition hover:bg-latte disabled:opacity-50"
              >
                Discard
              </button>
              <button
                type="button"
                onClick={handleApprove}
                disabled={status === "submitting"}
                data-testid="settings-approve"
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
