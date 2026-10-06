import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { EscalationApprovalCard } from "@/components/ResponseSection/EscalationApprovalCard";
import { useChatStore } from "@/store/chatStore";
import * as api from "@/lib/api";
import { newAssistantMessage, type ChatMessage } from "@/lib/chat";

vi.mock("@/lib/api");

function pendingMessage(overrides: Partial<ChatMessage> = {}): ChatMessage {
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

describe("EscalationApprovalCard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(api.approveEscalation).mockResolvedValue({
      request_id: "req-1",
      status: "acknowledged",
      approve: true,
    });
    useChatStore.setState({
      activeSessionId: "session-1",
      messages: { "session-1": [pendingMessage()] },
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
    useChatStore.setState({ activeSessionId: null, messages: {} });
  });

  it("renders the plain-language reason, premium alias, and cost", () => {
    render(<EscalationApprovalCard message={pendingMessage()} />);
    expect(screen.getByTestId("escalation-approval-reason")).toHaveTextContent(
      "cut off before finishing"
    );
    expect(screen.getByTestId("escalation-approval-premium-alias")).toHaveTextContent("Reserve Blend");
    expect(screen.getByTestId("escalation-approval-cost")).toHaveTextContent("$0.4200");
  });

  it("calls approveEscalation(true) and disables both buttons on Brew premium click", async () => {
    render(<EscalationApprovalCard message={pendingMessage()} />);
    fireEvent.click(screen.getByTestId("escalation-approve-button"));
    await waitFor(() => expect(api.approveEscalation).toHaveBeenCalledWith("req-1", true));
    expect(screen.getByTestId("escalation-approve-button")).toBeDisabled();
    expect(screen.getByTestId("escalation-decline-button")).toBeDisabled();
  });

  it("calls approveEscalation(false) on Keep the cheap cup click", async () => {
    render(<EscalationApprovalCard message={pendingMessage()} />);
    fireEvent.click(screen.getByTestId("escalation-decline-button"));
    await waitFor(() => expect(api.approveEscalation).toHaveBeenCalledWith("req-1", false));
  });

  it("ignores a rapid second click after the first (double-click safety)", async () => {
    render(<EscalationApprovalCard message={pendingMessage()} />);
    fireEvent.click(screen.getByTestId("escalation-approve-button"));
    fireEvent.click(screen.getByTestId("escalation-approve-button"));
    await waitFor(() => expect(api.approveEscalation).toHaveBeenCalledTimes(1));
  });

  it("shows a countdown derived from decisionDeadline", () => {
    render(<EscalationApprovalCard message={pendingMessage()} />);
    expect(screen.getByTestId("escalation-approval-countdown")).toHaveTextContent(/Auto-declining in \d+s/);
  });

  it("renders nothing when escalation is null", () => {
    const { container } = render(
      <EscalationApprovalCard message={{ ...pendingMessage(), escalation: null }} />
    );
    expect(container).toBeEmptyDOMElement();
  });
});
