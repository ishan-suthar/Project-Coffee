import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import {
  PANTRY_HINT_MIN_DROPPED_CHARS,
  RememberChatToggle,
} from "@/components/ResponseSection/RememberChatToggle";
import { useChatStore } from "@/store/chatStore";
import { newAssistantMessage } from "@/lib/chat";
import * as api from "@/lib/api";

vi.mock("@/lib/api");

const SESSION: import("@/lib/events").SessionSummary = {
  id: "session-1",
  project: "default",
  project_id: null,
  title: "First session",
  created_at: "2026-07-15T00:00:00Z",
  updated_at: "2026-07-15T00:00:00Z",
  cost_total_usd: 0,
  remember_chat: true,
};

describe("RememberChatToggle", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useChatStore.setState({ sessions: [SESSION] });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("reflects the session's current remember_chat state", () => {
    render(
      <RememberChatToggle
        sessionId="session-1"
        rememberChat
        lastAssistantMessage={null}
        hasAnyPriorAttachment={false}
      />
    );
    expect(screen.getByTestId("remember-chat-toggle")).toHaveAttribute("aria-checked", "true");
  });

  it("optimistically flips the sessions array immediately on click", async () => {
    let resolvePatch: () => void = () => {};
    vi.mocked(api.setRememberChat).mockReturnValue(
      new Promise((resolve) => {
        resolvePatch = () => resolve({ id: "session-1", remember_chat: false });
      })
    );

    render(
      <RememberChatToggle
        sessionId="session-1"
        rememberChat
        lastAssistantMessage={null}
        hasAnyPriorAttachment={false}
      />
    );
    fireEvent.click(screen.getByTestId("remember-chat-toggle"));

    await waitFor(() => {
      expect(useChatStore.getState().sessions[0].remember_chat).toBe(false);
    });
    resolvePatch();
  });

  it("rolls back the optimistic flip when the PATCH fails", async () => {
    vi.mocked(api.setRememberChat).mockRejectedValue(new Error("network error"));

    render(
      <RememberChatToggle
        sessionId="session-1"
        rememberChat
        lastAssistantMessage={null}
        hasAnyPriorAttachment={false}
      />
    );
    fireEvent.click(screen.getByTestId("remember-chat-toggle"));

    await waitFor(() => {
      expect(useChatStore.getState().sessions[0].remember_chat).toBe(true);
    });
  });

  it("shows the turn/token hint when ON and history was carried", () => {
    const message = {
      ...newAssistantMessage("req-1"),
      historyTurnsIncluded: 12,
      historyTokensEst: 4200,
    };
    render(
      <RememberChatToggle
        sessionId="session-1"
        rememberChat
        lastAssistantMessage={message}
        hasAnyPriorAttachment={false}
      />
    );
    expect(screen.getByTestId("remember-chat-hint")).toHaveTextContent("12 turns, ~4.2k tokens carried");
  });

  it("shows no hint when OFF, even if a prior message has history fields", () => {
    const message = {
      ...newAssistantMessage("req-1"),
      historyTurnsIncluded: 12,
      historyTokensEst: 4200,
    };
    render(
      <RememberChatToggle
        sessionId="session-1"
        rememberChat={false}
        lastAssistantMessage={message}
        hasAnyPriorAttachment={false}
      />
    );
    expect(screen.queryByTestId("remember-chat-hint")).not.toBeInTheDocument();
  });

  it("shows the attachment follow-up hint only when OFF and a prior message had an attachment", () => {
    render(
      <RememberChatToggle
        sessionId="session-1"
        rememberChat={false}
        lastAssistantMessage={null}
        hasAnyPriorAttachment
      />
    );
    expect(screen.getByTestId("remember-chat-attachment-hint")).toHaveTextContent(
      "Turn on Remember chat to ask follow-ups about your attachments."
    );
  });

  it("never shows the attachment hint when remember_chat is ON", () => {
    render(
      <RememberChatToggle
        sessionId="session-1"
        rememberChat
        lastAssistantMessage={null}
        hasAnyPriorAttachment
      />
    );
    expect(screen.queryByTestId("remember-chat-attachment-hint")).not.toBeInTheDocument();
  });

  // --- Brew 57: history trimming surfaced honestly --------------------

  function messageWithDrop(
    overrides: Partial<import("@/lib/chat").ChatMessage>
  ): import("@/lib/chat").ChatMessage {
    return {
      ...newAssistantMessage("req-1"),
      historyTurnsIncluded: 4,
      historyTokensEst: 900,
      ...overrides,
    };
  }

  function renderWithMessage(message: import("@/lib/chat").ChatMessage, rememberChat = true) {
    render(
      <RememberChatToggle
        sessionId="session-1"
        rememberChat={rememberChat}
        lastAssistantMessage={message}
        hasAnyPriorAttachment={false}
      />
    );
  }

  it("shows no drop notice when nothing was dropped (a real 0)", () => {
    renderWithMessage(
      messageWithDrop({
        historyTurnsDropped: 0,
        historyCharsDropped: 0,
        historyDropReason: null,
      })
    );
    expect(screen.queryByTestId("remember-chat-drop-notice")).not.toBeInTheDocument();
    // The "what was carried" hint still shows - silence is only about drops.
    expect(screen.getByTestId("remember-chat-hint")).toBeInTheDocument();
  });

  it("shows no drop notice when the fields are null (toggle was off)", () => {
    renderWithMessage(
      messageWithDrop({
        historyTurnsDropped: null,
        historyCharsDropped: null,
        historyDropReason: null,
      })
    );
    expect(screen.queryByTestId("remember-chat-drop-notice")).not.toBeInTheDocument();
  });

  it("reports ordinary window exhaustion", () => {
    renderWithMessage(
      messageWithDrop({
        historyTurnsDropped: 3,
        historyCharsDropped: 500,
        historyDropReason: "window_full",
      })
    );
    expect(screen.getByTestId("remember-chat-drop-notice")).toHaveTextContent(
      "3 earlier turns dropped to fit the window."
    );
  });

  it("uses the singular for exactly one dropped turn", () => {
    renderWithMessage(
      messageWithDrop({
        historyTurnsDropped: 1,
        historyCharsDropped: 500,
        historyDropReason: "window_full",
      })
    );
    expect(screen.getByTestId("remember-chat-drop-notice")).toHaveTextContent(
      "1 earlier turn dropped to fit the window."
    );
  });

  it("reports an oversized single turn distinctly from ordinary exhaustion", () => {
    renderWithMessage(
      messageWithDrop({
        historyTurnsDropped: 2,
        historyCharsDropped: 40000,
        historyDropReason: "single_turn_too_large",
      })
    );
    expect(screen.getByTestId("remember-chat-drop-notice")).toHaveTextContent(
      "too large for the window on its own"
    );
  });

  it("reports the current prompt filling the window with its own message", () => {
    renderWithMessage(
      messageWithDrop({
        historyTurnsDropped: 3,
        historyCharsDropped: 900,
        historyDropReason: "current_prompt_fills_window",
      })
    );
    expect(screen.getByTestId("remember-chat-drop-notice")).toHaveTextContent(
      "This message alone fills the history window, so no earlier turns were sent."
    );
  });

  it("suggests the Pantry when a single turn was too large, whatever the char count", () => {
    renderWithMessage(
      messageWithDrop({
        historyTurnsDropped: 1,
        historyCharsDropped: 10,
        historyDropReason: "single_turn_too_large",
      })
    );
    expect(screen.getByTestId("remember-chat-drop-notice")).toHaveTextContent(
      "Long documents belong in the Pantry"
    );
  });

  it("suggests the Pantry for a large ordinary drop", () => {
    renderWithMessage(
      messageWithDrop({
        historyTurnsDropped: 4,
        historyCharsDropped: PANTRY_HINT_MIN_DROPPED_CHARS,
        historyDropReason: "window_full",
      })
    );
    expect(screen.getByTestId("remember-chat-drop-notice")).toHaveTextContent(
      "Long documents belong in the Pantry"
    );
  });

  it("does not suggest the Pantry for a small ordinary drop", () => {
    renderWithMessage(
      messageWithDrop({
        historyTurnsDropped: 1,
        historyCharsDropped: PANTRY_HINT_MIN_DROPPED_CHARS - 1,
        historyDropReason: "window_full",
      })
    );
    const notice = screen.getByTestId("remember-chat-drop-notice");
    expect(notice).toBeInTheDocument();
    expect(notice).not.toHaveTextContent("Long documents belong in the Pantry");
  });

  it("never shows a drop notice when remember_chat is OFF", () => {
    renderWithMessage(
      messageWithDrop({
        historyTurnsDropped: 5,
        historyCharsDropped: 40000,
        historyDropReason: "single_turn_too_large",
      }),
      false
    );
    expect(screen.queryByTestId("remember-chat-drop-notice")).not.toBeInTheDocument();
  });
});
