import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MessageBubble } from "@/components/ResponseSection/MessageBubble";
import { newAssistantMessage, type ChatMessage } from "@/lib/chat";
import * as api from "@/lib/api";

vi.mock("@/lib/api");

function pendingEscalationMessage(overrides: Partial<ChatMessage> = {}): ChatMessage {
  const deadline = new Date(Date.now() + 60_000).toISOString();
  return {
    ...newAssistantMessage("req-1"),
    isStreaming: true,
    escalation: {
      reason: "truncated",
      estCostUsd: 0.42,
      premiumBeanAlias: "Reserve Blend",
      decisionDeadline: deadline,
    },
    latestEvent: {
      event: "escalation_pending",
      request_id: "req-1",
      ts: new Date().toISOString(),
      reason: "truncated",
      est_cost_usd: 0.42,
      premium_bean_alias: "Reserve Blend",
      decision_deadline: deadline,
    },
    ...overrides,
  };
}

describe("MessageBubble escalation approval card visibility", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.listBeans).mockResolvedValue([]);
  });

  it("shows the approval card while escalation_pending is the latest event and still streaming", () => {
    render(<MessageBubble message={pendingEscalationMessage()} />);
    expect(screen.getByTestId("escalation-approval-card")).toBeInTheDocument();
  });

  it("hides the card once a later event (e.g. escalating) has moved latestEvent past escalation_pending", () => {
    const message = pendingEscalationMessage({
      latestEvent: { event: "escalating", request_id: "req-1", ts: new Date().toISOString(), bean_alias: "Reserve Blend" },
    });
    render(<MessageBubble message={message} />);
    expect(screen.queryByTestId("escalation-approval-card")).not.toBeInTheDocument();
  });

  it("hides the card once isStreaming is false (recovered path resolved via polling)", () => {
    const message = pendingEscalationMessage({ isStreaming: false });
    render(<MessageBubble message={message} />);
    expect(screen.queryByTestId("escalation-approval-card")).not.toBeInTheDocument();
  });

  it("does not show the card for a message with no escalation at all", () => {
    render(<MessageBubble message={{ ...newAssistantMessage("req-2"), isStreaming: true }} />);
    expect(screen.queryByTestId("escalation-approval-card")).not.toBeInTheDocument();
  });

  it("shows the recovered note only for a pendingEscalationRecovered message", () => {
    render(<MessageBubble message={pendingEscalationMessage({ pendingEscalationRecovered: true })} />);
    expect(screen.getByTestId("recovered-escalation-note")).toBeInTheDocument();
  });

  it("does not show the recovered note for a normal live message", () => {
    render(<MessageBubble message={pendingEscalationMessage()} />);
    expect(screen.queryByTestId("recovered-escalation-note")).not.toBeInTheDocument();
  });
});
