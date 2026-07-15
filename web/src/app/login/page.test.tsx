import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import LoginPage from "@/app/login/page";
import * as api from "@/lib/api";

const push = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
}));

vi.mock("@/lib/api");

describe("LoginPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the heading and logo", () => {
    render(<LoginPage />);
    expect(screen.getByText("Sign in to Coffee Counter")).toBeInTheDocument();
  });

  it("Sign in button is disabled until both fields are filled", () => {
    render(<LoginPage />);
    const button = screen.getByRole("button", { name: /sign in/i });
    expect(button).toBeDisabled();

    fireEvent.change(screen.getByLabelText("Username"), { target: { value: "alice" } });
    expect(button).toBeDisabled();

    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "hunter2" } });
    expect(button).not.toBeDisabled();
  });

  it("submitting calls api.login and redirects to / on success", async () => {
    vi.mocked(api.login).mockResolvedValue({
      token: "tok",
      user: { id: 1, username: "alice", display_name: "Alice" },
    });

    render(<LoginPage />);
    fireEvent.change(screen.getByLabelText("Username"), { target: { value: "alice" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "hunter2" } });
    fireEvent.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => {
      expect(api.login).toHaveBeenCalledWith("alice", "hunter2");
      expect(push).toHaveBeenCalledWith("/");
    });
  });

  it("shows an error message on failed login", async () => {
    vi.mocked(api.login).mockRejectedValue(new Error("Invalid username or password."));

    render(<LoginPage />);
    fireEvent.change(screen.getByLabelText("Username"), { target: { value: "alice" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "wrong" } });
    fireEvent.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => {
      expect(screen.getByTestId("login-error")).toHaveTextContent("Invalid username or password.");
    });
    expect(push).not.toHaveBeenCalled();
  });
});
