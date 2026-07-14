import { describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { SessionMenu } from "@/components/Sidebar/SessionMenu";

describe("SessionMenu", () => {
  it("dropdown is closed by default", () => {
    render(<SessionMenu onCloseOutSession={vi.fn()} />);
    expect(screen.queryByTestId("session-menu-dropdown")).not.toBeInTheDocument();
  });

  it("opens the dropdown when the menu button is clicked", () => {
    render(<SessionMenu onCloseOutSession={vi.fn()} />);
    fireEvent.click(screen.getByTestId("session-menu-button"));
    expect(screen.getByTestId("session-menu-dropdown")).toBeInTheDocument();
  });

  it("calls onCloseOutSession and closes the dropdown when the item is clicked", () => {
    const onCloseOutSession = vi.fn();
    render(<SessionMenu onCloseOutSession={onCloseOutSession} />);
    fireEvent.click(screen.getByTestId("session-menu-button"));
    fireEvent.click(screen.getByTestId("close-out-session-item"));

    expect(onCloseOutSession).toHaveBeenCalledTimes(1);
    expect(screen.queryByTestId("session-menu-dropdown")).not.toBeInTheDocument();
  });

  it("clicking the menu button does not bubble up to a parent onClick", () => {
    const parentClick = vi.fn();
    render(
      <div onClick={parentClick}>
        <SessionMenu onCloseOutSession={vi.fn()} />
      </div>
    );
    fireEvent.click(screen.getByTestId("session-menu-button"));
    expect(parentClick).not.toHaveBeenCalled();
  });
});
