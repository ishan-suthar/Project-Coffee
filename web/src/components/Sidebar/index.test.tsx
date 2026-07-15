import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { Sidebar } from "@/components/Sidebar";
import { useChatStore } from "@/store/chatStore";
import * as api from "@/lib/api";
import * as authFetch from "@/lib/authFetch";

const push = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
}));

vi.mock("@/lib/api");

describe("Sidebar - Close out this session", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.listSessions).mockResolvedValue([]);
    vi.mocked(api.listProjects).mockResolvedValue([]);
    vi.mocked(api.generateMemoryProposal).mockResolvedValue({
      proposal_id: "proposal-1",
      files: [
        { path: "brew-log/active_context.md", diff: "", new_content: "x" },
        { path: "brew-log/progress.md", diff: "", new_content: "y" },
      ],
    });
    useChatStore.setState({
      projectFilter: "default",
      sessions: [
        {
          id: "session-1",
          project: "default",
          project_id: null,
          title: "First session",
          created_at: "2026-07-14T00:00:00Z",
          updated_at: "2026-07-14T00:00:00Z",
          cost_total_usd: 0,
          remember_chat: true,
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

  it("renaming a session shows an inline input and calls renameSession", () => {
    vi.mocked(api.renameSession).mockResolvedValue({ id: "session-1", title: "New title" });
    render(<Sidebar />);

    fireEvent.click(screen.getByTestId("session-menu-button"));
    fireEvent.click(screen.getByTestId("rename-session-item"));

    const input = screen.getByTestId("session-rename-input");
    fireEvent.change(input, { target: { value: "New title" } });
    fireEvent.keyDown(input, { key: "Enter" });

    expect(api.renameSession).toHaveBeenCalledWith("session-1", "New title");
  });

  it("deleting a session requires a confirm click, then calls deleteSession", () => {
    vi.mocked(api.deleteSession).mockResolvedValue(undefined);
    render(<Sidebar />);

    fireEvent.click(screen.getByTestId("session-menu-button"));
    fireEvent.click(screen.getByTestId("delete-session-item"));
    expect(api.deleteSession).not.toHaveBeenCalled();

    fireEvent.click(screen.getByTestId("confirm-delete-session-item"));
    expect(api.deleteSession).toHaveBeenCalledWith("session-1");
  });
});

describe("Sidebar - Settings", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.listSessions).mockResolvedValue([]);
    vi.mocked(api.listProjects).mockResolvedValue([]);
    useChatStore.setState({
      projectFilter: "default",
      sessions: [],
      sessionsLoaded: true,
      activeSessionId: null,
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
    useChatStore.setState({ sessions: [], sessionsLoaded: false, activeSessionId: null });
  });

  it("opens the SettingsPanel via the gear icon", () => {
    render(<Sidebar />);

    expect(screen.queryByTestId("settings-panel-overlay")).not.toBeInTheDocument();
    fireEvent.click(screen.getByTestId("open-settings-button"));
    expect(screen.getByTestId("settings-panel-overlay")).toBeInTheDocument();
  });

  it("closes the SettingsPanel via its Close button", () => {
    render(<Sidebar />);

    fireEvent.click(screen.getByTestId("open-settings-button"));
    fireEvent.click(screen.getByLabelText("Close settings"));
    expect(screen.queryByTestId("settings-panel-overlay")).not.toBeInTheDocument();
  });
});

describe("Sidebar - Auth", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.listSessions).mockResolvedValue([]);
    vi.mocked(api.listProjects).mockResolvedValue([]);
    vi.mocked(api.logout).mockResolvedValue(undefined);
    useChatStore.setState({
      projectFilter: "default",
      sessions: [],
      sessionsLoaded: true,
      activeSessionId: null,
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
    useChatStore.setState({ sessions: [], sessionsLoaded: false, activeSessionId: null });
  });

  it("shows the signed-in user's display name from local storage", () => {
    vi.spyOn(authFetch, "getStoredUser").mockReturnValue({
      id: 1,
      username: "alice",
      display_name: "Alice",
    });
    render(<Sidebar />);
    expect(screen.getByTestId("signed-in-as")).toHaveTextContent("Alice");
  });

  it("Sign out calls api.logout() and redirects to /login", async () => {
    render(<Sidebar />);
    fireEvent.click(screen.getByTestId("sign-out-button"));

    await waitFor(() => {
      expect(api.logout).toHaveBeenCalledTimes(1);
      expect(push).toHaveBeenCalledWith("/login");
    });
  });
});
