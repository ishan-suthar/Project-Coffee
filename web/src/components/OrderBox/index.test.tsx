import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { OrderBox } from "@/components/OrderBox";
import { useChatStore } from "@/store/chatStore";
import * as api from "@/lib/api";

vi.mock("@/lib/api");

describe("OrderBox - Use Pantry toggle", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.listBeans).mockResolvedValue([]);
    useChatStore.setState({
      activeSessionId: "session-1",
      activeRequestId: null,
      messages: {},
      sendPrompt: vi.fn().mockResolvedValue(undefined),
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
    useChatStore.setState({ activeSessionId: null, messages: {} });
  });

  it("defaults to off", () => {
    render(<OrderBox />);
    const toggle = screen.getByTestId("use-pantry-toggle") as HTMLInputElement;
    expect(toggle.checked).toBe(false);
  });

  it("sends usePantry: false when left unchecked", async () => {
    render(<OrderBox />);
    fireEvent.change(screen.getByPlaceholderText(/place your order/i), {
      target: { value: "What is the Ledger's cost_usd column for?" },
    });
    fireEvent.click(screen.getByText("Send"));

    expect(useChatStore.getState().sendPrompt).toHaveBeenCalledWith(
      "What is the Ledger's cost_usd column for?",
      expect.objectContaining({ usePantry: false })
    );
  });

  it("sends usePantry: true when checked before sending", async () => {
    render(<OrderBox />);
    fireEvent.click(screen.getByTestId("use-pantry-toggle"));
    fireEvent.change(screen.getByPlaceholderText(/place your order/i), {
      target: { value: "What is the Ledger's cost_usd column for?" },
    });
    fireEvent.click(screen.getByText("Send"));

    expect(useChatStore.getState().sendPrompt).toHaveBeenCalledWith(
      "What is the Ledger's cost_usd column for?",
      expect.objectContaining({ usePantry: true })
    );
  });

  it("use-web-toggle defaults to off", () => {
    render(<OrderBox />);
    const toggle = screen.getByTestId("use-web-toggle") as HTMLInputElement;
    expect(toggle.checked).toBe(false);
  });

  it("sends useWeb: false when left unchecked", async () => {
    render(<OrderBox />);
    fireEvent.change(screen.getByPlaceholderText(/place your order/i), {
      target: { value: "What's new in the latest Next.js release?" },
    });
    fireEvent.click(screen.getByText("Send"));

    expect(useChatStore.getState().sendPrompt).toHaveBeenCalledWith(
      "What's new in the latest Next.js release?",
      expect.objectContaining({ useWeb: false })
    );
  });

  it("sends useWeb: true when checked before sending", async () => {
    render(<OrderBox />);
    fireEvent.click(screen.getByTestId("use-web-toggle"));
    fireEvent.change(screen.getByPlaceholderText(/place your order/i), {
      target: { value: "What's new in the latest Next.js release?" },
    });
    fireEvent.click(screen.getByText("Send"));

    expect(useChatStore.getState().sendPrompt).toHaveBeenCalledWith(
      "What's new in the latest Next.js release?",
      expect.objectContaining({ useWeb: true })
    );
  });
});
