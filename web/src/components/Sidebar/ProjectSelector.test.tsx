import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { ProjectSelector } from "@/components/Sidebar/ProjectSelector";
import { useChatStore } from "@/store/chatStore";
import * as api from "@/lib/api";

vi.mock("@/lib/api");

describe("ProjectSelector", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.listProjects).mockResolvedValue([{ id: 1, name: "Recipes", created_at: "", updated_at: "" }]);
    vi.mocked(api.listSessions).mockResolvedValue([]);
    useChatStore.setState({ projectFilter: "default", projects: [], sessions: [], sessionsLoaded: false });
  });

  afterEach(() => {
    vi.restoreAllMocks();
    useChatStore.setState({ projectFilter: "default", projects: [], sessions: [], sessionsLoaded: false });
  });

  it("shows the current filter label on the button", () => {
    render(<ProjectSelector />);
    expect(screen.getByTestId("project-selector-button")).toHaveTextContent("default");
  });

  it("loads and lists real projects in the dropdown", async () => {
    render(<ProjectSelector />);
    fireEvent.click(screen.getByTestId("project-selector-button"));

    await waitFor(() => {
      expect(screen.getByText("Recipes")).toBeInTheDocument();
    });
  });

  it("selecting All chats sets projectFilter to 'all'", async () => {
    render(<ProjectSelector />);
    fireEvent.click(screen.getByTestId("project-selector-button"));
    fireEvent.click(screen.getByText("All chats"));

    expect(useChatStore.getState().projectFilter).toBe("all");
  });

  it("selecting a real project sets projectFilter to that project", async () => {
    render(<ProjectSelector />);
    fireEvent.click(screen.getByTestId("project-selector-button"));
    await waitFor(() => screen.getByTestId("project-selector-item"));
    fireEvent.click(screen.getByTestId("project-selector-item"));

    expect(useChatStore.getState().projectFilter).toEqual({
      id: 1,
      name: "Recipes",
      created_at: "",
      updated_at: "",
    });
  });

  it("creating a new project calls api.createProject", async () => {
    vi.mocked(api.createProject).mockResolvedValue({ id: 2, name: "New one", created_at: "", updated_at: "" });
    render(<ProjectSelector />);
    fireEvent.click(screen.getByTestId("project-selector-button"));
    fireEvent.click(screen.getByTestId("new-project-button"));

    const input = screen.getByPlaceholderText("Project name");
    fireEvent.change(input, { target: { value: "New one" } });
    fireEvent.click(screen.getByText("Create"));

    await waitFor(() => {
      expect(api.createProject).toHaveBeenCalledWith("New one");
    });
  });

  it("renaming a project calls api.renameProject", async () => {
    vi.mocked(api.renameProject).mockResolvedValue({ id: 1, name: "Renamed" });
    render(<ProjectSelector />);
    fireEvent.click(screen.getByTestId("project-selector-button"));
    await waitFor(() => screen.getByLabelText("Rename Recipes"));
    fireEvent.click(screen.getByLabelText("Rename Recipes"));

    const input = screen.getByDisplayValue("Recipes");
    fireEvent.change(input, { target: { value: "Renamed" } });
    fireEvent.keyDown(input, { key: "Enter" });

    await waitFor(() => {
      expect(api.renameProject).toHaveBeenCalledWith(1, "Renamed");
    });
  });

  it("deleting a project calls api.deleteProject", async () => {
    vi.mocked(api.deleteProject).mockResolvedValue(undefined);
    render(<ProjectSelector />);
    fireEvent.click(screen.getByTestId("project-selector-button"));
    await waitFor(() => screen.getByLabelText("Delete Recipes"));
    fireEvent.click(screen.getByLabelText("Delete Recipes"));

    await waitFor(() => {
      expect(api.deleteProject).toHaveBeenCalledWith(1);
    });
  });
});
