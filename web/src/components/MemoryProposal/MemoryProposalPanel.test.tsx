import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryProposalPanel } from "@/components/MemoryProposal/MemoryProposalPanel";
import * as api from "@/lib/api";

vi.mock("@/lib/api");

const SAMPLE_RESULT = {
  proposal_id: "proposal-1",
  files: [
    {
      path: "brew-log/active_context.md",
      diff: "--- a/brew-log/active_context.md\n+++ b/brew-log/active_context.md\n@@ -1,1 +1,2 @@\n line one\n+line two\n",
      new_content: "line one\nline two\n",
    },
    {
      path: "brew-log/progress.md",
      diff: "",
      new_content: "unchanged\n",
    },
  ],
};

describe("MemoryProposalPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("shows a loading state, then the diffs for both files", async () => {
    vi.mocked(api.generateMemoryProposal).mockResolvedValue(SAMPLE_RESULT);
    render(<MemoryProposalPanel sessionId="session-1" onClose={vi.fn()} />);

    expect(screen.getByTestId("memory-proposal-loading")).toBeInTheDocument();
    expect(api.generateMemoryProposal).toHaveBeenCalledWith("session-1");

    await waitFor(() => {
      expect(screen.getAllByTestId("diff-view")).toHaveLength(1);
    });
    expect(screen.getByText("brew-log/active_context.md")).toBeInTheDocument();
    expect(screen.getByText("brew-log/progress.md")).toBeInTheDocument();
    expect(screen.getByText(/No changes proposed for this file\./)).toBeInTheDocument();
  });

  it("shows an error and no approve/discard buttons when generation fails", async () => {
    vi.mocked(api.generateMemoryProposal).mockRejectedValue(
      new Error("POST /v1/sessions/session-1/memory_proposal failed with 422: bad")
    );
    render(<MemoryProposalPanel sessionId="session-1" onClose={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getByTestId("memory-proposal-error")).toHaveTextContent("422");
    });
    expect(screen.queryByTestId("memory-proposal-approve")).not.toBeInTheDocument();
  });

  it("approving calls approveMemoryProposal with the right id and closes the panel", async () => {
    vi.mocked(api.generateMemoryProposal).mockResolvedValue(SAMPLE_RESULT);
    vi.mocked(api.approveMemoryProposal).mockResolvedValue({
      proposal_id: "proposal-1",
      status: "approved",
    });
    const onClose = vi.fn();
    render(<MemoryProposalPanel sessionId="session-1" onClose={onClose} />);

    await waitFor(() => screen.getByTestId("memory-proposal-approve"));
    fireEvent.click(screen.getByTestId("memory-proposal-approve"));

    await waitFor(() => {
      expect(api.approveMemoryProposal).toHaveBeenCalledWith("proposal-1");
      expect(onClose).toHaveBeenCalledTimes(1);
    });
  });

  it("discarding calls discardMemoryProposal with the right id and closes the panel", async () => {
    vi.mocked(api.generateMemoryProposal).mockResolvedValue(SAMPLE_RESULT);
    vi.mocked(api.discardMemoryProposal).mockResolvedValue({
      proposal_id: "proposal-1",
      status: "discarded",
    });
    const onClose = vi.fn();
    render(<MemoryProposalPanel sessionId="session-1" onClose={onClose} />);

    await waitFor(() => screen.getByTestId("memory-proposal-discard"));
    fireEvent.click(screen.getByTestId("memory-proposal-discard"));

    await waitFor(() => {
      expect(api.discardMemoryProposal).toHaveBeenCalledWith("proposal-1");
      expect(onClose).toHaveBeenCalledTimes(1);
    });
    expect(api.approveMemoryProposal).not.toHaveBeenCalled();
  });

  it("clicking Close calls onClose without approving or discarding", async () => {
    vi.mocked(api.generateMemoryProposal).mockResolvedValue(SAMPLE_RESULT);
    const onClose = vi.fn();
    render(<MemoryProposalPanel sessionId="session-1" onClose={onClose} />);

    await waitFor(() => screen.getByTestId("memory-proposal-approve"));
    fireEvent.click(screen.getByLabelText("Close proposal panel"));

    expect(onClose).toHaveBeenCalledTimes(1);
    expect(api.approveMemoryProposal).not.toHaveBeenCalled();
    expect(api.discardMemoryProposal).not.toHaveBeenCalled();
  });
});
