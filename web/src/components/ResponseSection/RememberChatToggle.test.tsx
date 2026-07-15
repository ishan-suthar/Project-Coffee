import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { RememberChatToggle } from "@/components/ResponseSection/RememberChatToggle";
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
});
