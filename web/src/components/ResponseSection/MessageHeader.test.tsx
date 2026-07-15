import { describe, expect, it } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MessageHeader } from "@/components/ResponseSection/MessageHeader";
import { newAssistantMessage } from "@/lib/chat";
import type { ChatMessage } from "@/lib/chat";

function completedMessage(overrides: Partial<ChatMessage> = {}): ChatMessage {
  return {
    ...newAssistantMessage("req-1"),
    isStreaming: false,
    beanAlias: "House Blend",
    costUsd: 0.0042,
    latencyMs: 1234,
    ...overrides,
  };
}

describe("MessageHeader", () => {
  it("renders the bean alias badge", () => {
    render(<MessageHeader message={completedMessage()} />);
    expect(screen.getByTestId("bean-alias-badge")).toHaveTextContent("House Blend");
  });

  it("renders the cost pill formatted to 4 decimal places", () => {
    render(<MessageHeader message={completedMessage({ costUsd: 0.1 })} />);
    expect(screen.getByTestId("cost-pill")).toHaveTextContent("$0.1000");
  });

  it("renders latency in milliseconds", () => {
    render(<MessageHeader message={completedMessage({ latencyMs: 2500 })} />);
    expect(screen.getByText("2500ms")).toBeInTheDocument();
  });

  it("does not render a bean alias badge when beanAlias is null", () => {
    render(<MessageHeader message={completedMessage({ beanAlias: null })} />);
    expect(screen.queryByTestId("bean-alias-badge")).not.toBeInTheDocument();
  });

  it("renders the draft-quality tag when draftQuality is true", () => {
    render(<MessageHeader message={completedMessage({ draftQuality: true })} />);
    expect(screen.getByTestId("draft-quality-tag")).toHaveTextContent("draft, not escalated");
  });

  it("does not render the draft-quality tag when draftQuality is false", () => {
    render(<MessageHeader message={completedMessage({ draftQuality: false })} />);
    expect(screen.queryByTestId("draft-quality-tag")).not.toBeInTheDocument();
  });

  it("renders an escalation marker when escalation data is present", () => {
    render(
      <MessageHeader
        message={completedMessage({
          escalation: {
            reason: "truncated",
            estCostUsd: 0.5,
            premiumBeanAlias: "Reserve Blend",
            decisionDeadline: null,
          },
        })}
      />
    );
    expect(screen.getByTestId("escalation-marker")).toHaveTextContent("escalation: truncated");
  });

  it("expands escalation detail on click", () => {
    render(
      <MessageHeader
        message={completedMessage({
          escalation: {
            reason: "empty",
            estCostUsd: 0.25,
            premiumBeanAlias: "Reserve Blend",
            decisionDeadline: null,
          },
        })}
      />
    );
    expect(screen.queryByTestId("escalation-detail")).not.toBeInTheDocument();
    fireEvent.click(screen.getByTestId("escalation-marker"));
    expect(screen.getByTestId("escalation-detail")).toBeInTheDocument();
    expect(screen.getByTestId("escalation-detail")).toHaveTextContent("Reserve Blend");
  });

  it("shows 'none configured' when premiumBeanAlias is null (no premium Bean gap)", () => {
    render(
      <MessageHeader
        message={completedMessage({
          escalation: { reason: "empty", estCostUsd: 0, premiumBeanAlias: null, decisionDeadline: null },
        })}
      />
    );
    fireEvent.click(screen.getByTestId("escalation-marker"));
    expect(screen.getByTestId("escalation-detail")).toHaveTextContent("none configured");
  });

  it("does not render an escalation marker when escalation is null", () => {
    render(<MessageHeader message={completedMessage({ escalation: null })} />);
    expect(screen.queryByTestId("escalation-marker")).not.toBeInTheDocument();
  });

  it("renders the badge row on one line, small and muted", () => {
    render(<MessageHeader message={completedMessage()} />);
    expect(screen.getByTestId("message-header")).toHaveClass("flex-nowrap", "text-[11px]");
    expect(screen.getByTestId("bean-alias-badge")).toHaveClass("text-medium-roast");
  });
});
