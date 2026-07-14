import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { Sidebar } from "@/components/Sidebar";
import { useChatStore } from "@/store/chatStore";
import * as api from "@/lib/api";

vi.mock("@/lib/api");

describe("Sidebar - Close out this session", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.listSessions).mockResolvedValue([]);
    vi.mocked(api.generateMemoryProposal).mockResolvedValue({
      proposal_id: "proposal-1",
      files: [
        { path: "brew-log/active_context.md", diff: "", new_content: "x" },
        { path: "brew-log/progress.md", diff: "", new_content: "y" },
      ],
    });
    useChatStore.setState({
      project: "default",
      sessions: [
        {
          id: "session-1",
          project: "default",
          title: "First session",
          created_at: "2026-07-14T00:00:00Z",
          updated_at: "2026-07-14T00:00:00Z",
          cost_total_usd: 0,
        },
      ],
      sessionsLoaded: true,
      activeSessionId: null,
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
    useChatStore.setState({ sessions: [], sessionsLoaded: false, activeSessionId: null });
  });

  it("opens the MemoryProposalPanel for the right session via the session menu", async () => {
    render(<Sidebar />);

    fireEvent.click(screen.getByTestId("session-menu-button"));
    fireEvent.click(screen.getByTestId("close-out-session-item"));

    expect(screen.getByTestId("memory-proposal-overlay")).toBeInTheDocument();
    await waitFor(() => {
      expect(api.generateMemoryProposal).toHaveBeenCalledWith("session-1");
    });
  });

  it("clicking the session menu does not also select the session", () => {
    render(<Sidebar />);

    fireEvent.click(screen.getByTestId("session-menu-button"));

    expect(useChatStore.getState().activeSessionId).toBeNull();
  });
});
