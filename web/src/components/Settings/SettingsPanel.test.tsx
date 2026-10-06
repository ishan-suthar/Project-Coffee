import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { SettingsPanel } from "@/components/Settings/SettingsPanel";
import * as api from "@/lib/api";

vi.mock("@/lib/api");

describe("SettingsPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("starts idle with a Rebuild House Blend button", () => {
    render(<SettingsPanel onClose={vi.fn()} />);
    expect(screen.getByTestId("rebuild-house-blend-button")).toBeInTheDocument();
    expect(api.rebuildPolicyPreview).not.toHaveBeenCalled();
  });

  it("clicking Rebuild House Blend fetches and shows the diff", async () => {
    vi.mocked(api.rebuildPolicyPreview).mockResolvedValue({
      proposal_id: "proposal-1",
      diff: "--- a\n+++ b\n@@ -1 +1 @@\n-old\n+new\n",
      escalation_candidates: [],
    });

    render(<SettingsPanel onClose={vi.fn()} />);
    fireEvent.click(screen.getByTestId("rebuild-house-blend-button"));

    expect(api.rebuildPolicyPreview).toHaveBeenCalledTimes(1);
    await waitFor(() => {
      expect(screen.getByTestId("diff-view")).toBeInTheDocument();
    });
    expect(screen.queryByTestId("escalation-candidates-warning")).not.toBeInTheDocument();
  });

  it("shows the escalation-candidates warning when present", async () => {
    vi.mocked(api.rebuildPolicyPreview).mockResolvedValue({
      proposal_id: "proposal-1",
      diff: "",
      escalation_candidates: ["code", "explain"],
    });

    render(<SettingsPanel onClose={vi.fn()} />);
    fireEvent.click(screen.getByTestId("rebuild-house-blend-button"));

    await waitFor(() => {
      expect(screen.getByTestId("escalation-candidates-warning")).toHaveTextContent("code");
      expect(screen.getByTestId("escalation-candidates-warning")).toHaveTextContent("explain");
    });
  });

  it("shows an error when preview fails", async () => {
    vi.mocked(api.rebuildPolicyPreview).mockRejectedValue(new Error("boom"));

    render(<SettingsPanel onClose={vi.fn()} />);
    fireEvent.click(screen.getByTestId("rebuild-house-blend-button"));

    await waitFor(() => {
      expect(screen.getByTestId("settings-error")).toHaveTextContent("boom");
    });
  });

  it("approving calls rebuildPolicyApply with the right id and shows applied state", async () => {
    vi.mocked(api.rebuildPolicyPreview).mockResolvedValue({
      proposal_id: "proposal-1",
      diff: "some diff",
      escalation_candidates: [],
    });
    vi.mocked(api.rebuildPolicyApply).mockResolvedValue({ proposal_id: "proposal-1", status: "applied" });

    render(<SettingsPanel onClose={vi.fn()} />);
    fireEvent.click(screen.getByTestId("rebuild-house-blend-button"));
    await waitFor(() => screen.getByTestId("settings-approve"));
    fireEvent.click(screen.getByTestId("settings-approve"));

    await waitFor(() => {
      expect(api.rebuildPolicyApply).toHaveBeenCalledWith("proposal-1");
      expect(screen.getByTestId("settings-applied")).toBeInTheDocument();
    });
  });

  it("discarding calls rebuildPolicyDiscard and resets to idle", async () => {
    vi.mocked(api.rebuildPolicyPreview).mockResolvedValue({
      proposal_id: "proposal-1",
      diff: "some diff",
      escalation_candidates: [],
    });
    vi.mocked(api.rebuildPolicyDiscard).mockResolvedValue({ proposal_id: "proposal-1", status: "discarded" });

    render(<SettingsPanel onClose={vi.fn()} />);
    fireEvent.click(screen.getByTestId("rebuild-house-blend-button"));
    await waitFor(() => screen.getByTestId("settings-discard"));
    fireEvent.click(screen.getByTestId("settings-discard"));

    await waitFor(() => {
      expect(api.rebuildPolicyDiscard).toHaveBeenCalledWith("proposal-1");
      expect(screen.getByTestId("rebuild-house-blend-button")).toBeInTheDocument();
    });
    expect(api.rebuildPolicyApply).not.toHaveBeenCalled();
  });

  it("clicking Close calls onClose without approving or discarding", () => {
    const onClose = vi.fn();
    render(<SettingsPanel onClose={onClose} />);
    fireEvent.click(screen.getByLabelText("Close settings"));

    expect(onClose).toHaveBeenCalledTimes(1);
    expect(api.rebuildPolicyApply).not.toHaveBeenCalled();
    expect(api.rebuildPolicyDiscard).not.toHaveBeenCalled();
  });
});
