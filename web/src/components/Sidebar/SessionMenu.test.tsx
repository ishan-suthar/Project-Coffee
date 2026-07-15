import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { SessionMenu } from "@/components/Sidebar/SessionMenu";

function renderMenu(overrides: Partial<Parameters<typeof SessionMenu>[0]> = {}) {
  const props = {
    onCloseOutSession: vi.fn(),
    onRename: vi.fn(),
    onDelete: vi.fn(),
    ...overrides,
  };
  render(<SessionMenu {...props} />);
  return props;
}

describe("SessionMenu", () => {
  it("dropdown is closed by default", () => {
    renderMenu();
    expect(screen.queryByTestId("session-menu-dropdown")).not.toBeInTheDocument();
  });

  it("opens the dropdown when the menu button is clicked", () => {
    renderMenu();
    fireEvent.click(screen.getByTestId("session-menu-button"));
    expect(screen.getByTestId("session-menu-dropdown")).toBeInTheDocument();
  });

  it("calls onCloseOutSession and closes the dropdown when the item is clicked", () => {
    const props = renderMenu();
    fireEvent.click(screen.getByTestId("session-menu-button"));
    fireEvent.click(screen.getByTestId("close-out-session-item"));

    expect(props.onCloseOutSession).toHaveBeenCalledTimes(1);
    expect(screen.queryByTestId("session-menu-dropdown")).not.toBeInTheDocument();
  });

  it("calls onRename and closes the dropdown when Rename is clicked", () => {
    const props = renderMenu();
    fireEvent.click(screen.getByTestId("session-menu-button"));
    fireEvent.click(screen.getByTestId("rename-session-item"));

    expect(props.onRename).toHaveBeenCalledTimes(1);
    expect(screen.queryByTestId("session-menu-dropdown")).not.toBeInTheDocument();
  });

  it("Delete requires a second confirm click before calling onDelete", () => {
    const props = renderMenu();
    fireEvent.click(screen.getByTestId("session-menu-button"));
    fireEvent.click(screen.getByTestId("delete-session-item"));
    expect(props.onDelete).not.toHaveBeenCalled();
    expect(screen.getByTestId("confirm-delete-session-item")).toBeInTheDocument();

    fireEvent.click(screen.getByTestId("confirm-delete-session-item"));
    expect(props.onDelete).toHaveBeenCalledTimes(1);
    expect(screen.queryByTestId("session-menu-dropdown")).not.toBeInTheDocument();
  });

  it("clicking the menu button does not bubble up to a parent onClick", () => {
    const parentClick = vi.fn();
    render(
      <div onClick={parentClick}>
        <SessionMenu onCloseOutSession={vi.fn()} onRename={vi.fn()} onDelete={vi.fn()} />
      </div>
    );
    fireEvent.click(screen.getByTestId("session-menu-button"));
    expect(parentClick).not.toHaveBeenCalled();
  });
});
