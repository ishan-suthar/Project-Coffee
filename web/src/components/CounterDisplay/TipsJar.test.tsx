import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, render, screen } from "@testing-library/react";
import { TipsJar } from "@/components/CounterDisplay/TipsJar";
import type { GeneratingEvent } from "@/lib/events";

function generatingEvent(ts: string): GeneratingEvent {
  return { event: "generating", request_id: "r1", ts, tokens_out: 1, est_cost_usd: 0, text_delta: "x" };
}

describe("TipsJar", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("renders the formatted running total", () => {
    render(<TipsJar sessionCostUsd={0.1234} event={null} />);
    expect(screen.getByTestId("tips-jar-total")).toHaveTextContent("$0.1234");
  });

  it("drops one coin on a generating event", () => {
    const { rerender } = render(<TipsJar sessionCostUsd={0} event={null} />);
    vi.setSystemTime(1000);
    rerender(<TipsJar sessionCostUsd={0} event={generatingEvent("t1")} />);
    expect(screen.getAllByTestId("tips-jar-coin")).toHaveLength(1);
  });

  it("throttles a second coin within 500ms of the first", () => {
    const { rerender } = render(<TipsJar sessionCostUsd={0} event={null} />);
    vi.setSystemTime(1000);
    rerender(<TipsJar sessionCostUsd={0} event={generatingEvent("t1")} />);
    vi.setSystemTime(1200);
    rerender(<TipsJar sessionCostUsd={0} event={generatingEvent("t2")} />);
    expect(screen.getAllByTestId("tips-jar-coin")).toHaveLength(1);
  });

  it("allows a second coin once 500ms has passed", () => {
    const { rerender } = render(<TipsJar sessionCostUsd={0} event={null} />);
    vi.setSystemTime(1000);
    rerender(<TipsJar sessionCostUsd={0} event={generatingEvent("t1")} />);
    vi.setSystemTime(1600);
    rerender(<TipsJar sessionCostUsd={0} event={generatingEvent("t2")} />);
    expect(screen.getAllByTestId("tips-jar-coin")).toHaveLength(2);
  });

  it("does not drop a second coin for the exact same event re-rendered", () => {
    const { rerender } = render(<TipsJar sessionCostUsd={0} event={null} />);
    vi.setSystemTime(1000);
    const evt = generatingEvent("t1");
    rerender(<TipsJar sessionCostUsd={0} event={evt} />);
    rerender(<TipsJar sessionCostUsd={0} event={evt} />);
    expect(screen.getAllByTestId("tips-jar-coin")).toHaveLength(1);
  });

  it("removes a coin element once its drop animation window elapses", () => {
    const { rerender } = render(<TipsJar sessionCostUsd={0} event={null} />);
    vi.setSystemTime(1000);
    rerender(<TipsJar sessionCostUsd={0} event={generatingEvent("t1")} />);
    expect(screen.getAllByTestId("tips-jar-coin")).toHaveLength(1);
    act(() => {
      vi.advanceTimersByTime(700);
    });
    expect(screen.queryByTestId("tips-jar-coin")).not.toBeInTheDocument();
  });

  it("the total persists exactly as given, unmodified, on a non-generating event", () => {
    render(<TipsJar sessionCostUsd={0.5} event={{ event: "classifying", request_id: "r1", ts: "t1" }} />);
    expect(screen.getByTestId("tips-jar-total")).toHaveTextContent("$0.5000");
  });
});
