import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useChatStore } from "@/store/chatStore";
import * as api from "@/lib/api";
import { newAssistantMessage } from "@/lib/chat";

vi.mock("@/lib/api");

describe("chatStore escalation actions", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useChatStore.setState({
      activeSessionId: "session-1",
      messages: {},
      sessions: [],
      sessionsLoaded: false,
      activeRequestId: null,
      abortController: null,
    });
  });

  afterEach(() => {
    useChatStore.setState({ activeSessionId: null, messages: {} });
  });

  describe("approveEscalation", () => {
    it("calls api.approveEscalation with the given decision", async () => {
      vi.mocked(api.approveEscalation).mockResolvedValue({
        request_id: "req-1",
        status: "acknowledged",
        approve: true,
      });
      useChatStore.setState({
        messages: { "session-1": [{ ...newAssistantMessage("req-1"), isStreaming: true }] },
      });

      await useChatStore.getState().approveEscalation("req-1", true);

      expect(api.approveEscalation).toHaveBeenCalledWith("req-1", true);
    });

    it("does not poll for a live (non-recovered) message", async () => {
      vi.mocked(api.approveEscalation).mockResolvedValue({
        request_id: "req-1",
        status: "acknowledged",
        approve: true,
      });
      useChatStore.setState({
        messages: {
          "session-1": [{ ...newAssistantMessage("req-1"), isStreaming: true, pendingEscalationRecovered: false }],
        },
      });

      await useChatStore.getState().approveEscalation("req-1", true);

      expect(api.getSessionMessages).not.toHaveBeenCalled();
    });

    it("polls GET /v1/sessions/{id}/messages for a recovered message until the result appears", async () => {
      vi.useFakeTimers();
      vi.mocked(api.approveEscalation).mockResolvedValue({
        request_id: "req-1",
        status: "acknowledged",
        approve: false,
      });
      vi.mocked(api.getSessionMessages)
        .mockResolvedValueOnce([]) // first poll: not there yet
        .mockResolvedValueOnce([
          {
            id: "msg-1",
            request_id: "req-1",
            role: "assistant",
            content: "Here is the draft answer.",
            bean_alias: "House Blend",
            task_type: "explain",
            complexity: "espresso_shot",
            cost_usd: 0,
            latency_ms: 500,
            escalated: false,
            draft_quality: true,
            rating: null,
            created_at: "2026-07-12T20:20:00Z",
            has_attachments: false,
          },
        ]);

      useChatStore.setState({
        messages: {
          "session-1": [
            { ...newAssistantMessage("req-1"), isStreaming: true, pendingEscalationRecovered: true },
          ],
        },
      });

      const done = useChatStore.getState().approveEscalation("req-1", false);
      await vi.advanceTimersByTimeAsync(2000); // first poll tick: empty
      await vi.advanceTimersByTimeAsync(2000); // second poll tick: found
      await done;

      const message = useChatStore.getState().messages["session-1"][0];
      expect(message.content).toBe("Here is the draft answer.");
      expect(message.isStreaming).toBe(false);
      expect(message.draftQuality).toBe(true);

      vi.useRealTimers();
    });
  });

  describe("recoverPendingEscalation", () => {
    it("appends a synthetic pending message when the router reports one", async () => {
      vi.mocked(api.getPendingEscalation).mockResolvedValue({
        request_id: "req-recovered",
        reason: "empty",
        est_cost_usd: 0.1,
        premium_bean_alias: "Reserve Blend",
        started_at: "2026-07-12T20:00:00Z",
        decision_deadline: "2026-07-12T20:10:00Z",
      });

      await useChatStore.getState().recoverPendingEscalation("session-1");

      const messages = useChatStore.getState().messages["session-1"];
      expect(messages).toHaveLength(1);
      expect(messages[0].requestId).toBe("req-recovered");
      expect(messages[0].pendingEscalationRecovered).toBe(true);
      expect(messages[0].escalation?.premiumBeanAlias).toBe("Reserve Blend");
    });

    it("does nothing when no escalation is pending", async () => {
      vi.mocked(api.getPendingEscalation).mockResolvedValue(null);

      await useChatStore.getState().recoverPendingEscalation("session-1");

      expect(useChatStore.getState().messages["session-1"] ?? []).toHaveLength(0);
    });

    it("does not duplicate an already-recovered card on a second call", async () => {
      vi.mocked(api.getPendingEscalation).mockResolvedValue({
        request_id: "req-recovered",
        reason: "empty",
        est_cost_usd: 0.1,
        premium_bean_alias: "Reserve Blend",
        started_at: "2026-07-12T20:00:00Z",
        decision_deadline: "2026-07-12T20:10:00Z",
      });

      await useChatStore.getState().recoverPendingEscalation("session-1");
      await useChatStore.getState().recoverPendingEscalation("session-1");

      expect(useChatStore.getState().messages["session-1"]).toHaveLength(1);
    });
  });
});
