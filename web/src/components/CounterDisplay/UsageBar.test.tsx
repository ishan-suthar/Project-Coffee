import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { UsageBar } from "@/components/CounterDisplay/UsageBar";
import type { CompleteEvent } from "@/lib/events";
import * as api from "@/lib/api";

vi.mock("@/lib/api");

function completeEvent(): CompleteEvent {
  return {
    event: "complete",
    request_id: "r1",
    ts: "t1",
    bean_alias: "House Blend",
    tokens_in: 10,
    tokens_out: 10,
    cost_usd: 0.01,
    latency_ms: 100,
    escalated: false,
    draft_quality: false,
    pantry_sources: null,
    history_turns: null,
    history_tokens_est: null,
    history_turns_dropped: null,
    history_chars_dropped: null,
    history_drop_reason: null,
    web_sources: null,
  };
}

describe("UsageBar", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders nothing until the first fetch resolves", () => {
    vi.mocked(api.getUsage).mockReturnValue(new Promise(() => {}));
    render(<UsageBar event={null} />);
    expect(screen.queryByTestId("usage-bar")).not.toBeInTheDocument();
  });

  it("shows normal-level styling well under the cap", async () => {
    vi.mocked(api.getUsage).mockResolvedValue({ todaySpendUsd: 0.1, capUsd: 1.0, resetAt: "2026-07-18T00:00:00Z" });
    render(<UsageBar event={null} />);
    await waitFor(() => expect(screen.getByTestId("usage-bar")).toHaveAttribute("data-level", "normal"));
    expect(screen.getByTestId("usage-bar-text")).toHaveTextContent("$0.10 of $1.00 today");
  });

  it("turns amber (warning) at 80% of the cap", async () => {
    vi.mocked(api.getUsage).mockResolvedValue({ todaySpendUsd: 0.8, capUsd: 1.0, resetAt: "2026-07-18T00:00:00Z" });
    render(<UsageBar event={null} />);
    await waitFor(() => expect(screen.getByTestId("usage-bar")).toHaveAttribute("data-level", "warning"));
  });

  it("turns red (critical) at the cap", async () => {
    vi.mocked(api.getUsage).mockResolvedValue({ todaySpendUsd: 1.0, capUsd: 1.0, resetAt: "2026-07-18T00:00:00Z" });
    render(<UsageBar event={null} />);
    await waitFor(() => expect(screen.getByTestId("usage-bar")).toHaveAttribute("data-level", "critical"));
  });

  it("refetches on a new complete event", async () => {
    vi.mocked(api.getUsage).mockResolvedValue({ todaySpendUsd: 0.1, capUsd: 1.0, resetAt: "2026-07-18T00:00:00Z" });
    const { rerender } = render(<UsageBar event={null} />);
    await waitFor(() => expect(api.getUsage).toHaveBeenCalledTimes(1));

    vi.mocked(api.getUsage).mockResolvedValue({ todaySpendUsd: 0.9, capUsd: 1.0, resetAt: "2026-07-18T00:00:00Z" });
    rerender(<UsageBar event={completeEvent()} />);
    await waitFor(() => expect(api.getUsage).toHaveBeenCalledTimes(2));
    await waitFor(() => expect(screen.getByTestId("usage-bar")).toHaveAttribute("data-level", "warning"));
  });

  it("fails silently when the router is unreachable", async () => {
    vi.mocked(api.getUsage).mockRejectedValue(new Error("network error"));
    render(<UsageBar event={null} />);
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(screen.queryByTestId("usage-bar")).not.toBeInTheDocument();
  });
});
