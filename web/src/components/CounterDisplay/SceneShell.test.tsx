import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { SceneShell } from "@/components/CounterDisplay/SceneShell";
import * as preferences from "@/lib/preferences";
import type { GeneratingEvent } from "@/lib/events";

vi.mock("@/lib/preferences");

// BaristaScene needs a real WASM/canvas context jsdom can't provide -
// stubbed here to a prop-capturing component so this file can test
// SceneShell's own collapse/fade-zone/caption wiring in isolation, the
// same way BaristaScene.test.tsx separately covers the Rive tier logic.
let lastBaristaSceneProps: Record<string, unknown> | null = null;
vi.mock("@/components/CounterDisplay/BaristaScene", () => ({
  BaristaScene: (props: Record<string, unknown>) => {
    lastBaristaSceneProps = props;
    return <div data-testid="mock-barista-scene" />;
  },
}));

function generatingEvent(ts: string): GeneratingEvent {
  return { event: "generating", request_id: "r1", ts, tokens_out: 1, est_cost_usd: 0, text_delta: "x" };
}

describe("SceneShell", () => {
  beforeEach(() => {
    lastBaristaSceneProps = null;
    vi.mocked(preferences.getPreferences).mockResolvedValue({});
    vi.mocked(preferences.setPreference).mockResolvedValue(undefined);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("starts expanded by default when no preference is stored", async () => {
    render(
      <SceneShell
        event={null}
        sessionCostUsd={0}
        beanAlias={null}
        complexity={null}
        hasVisibleContent={false}
        reducedMotion={false}
      />
    );
    await waitFor(() => expect(preferences.getPreferences).toHaveBeenCalled());
    expect(screen.getByTestId("scene-shell")).toHaveAttribute("data-collapsed", "false");
  });

  it("starts collapsed when the stored preference says so", async () => {
    vi.mocked(preferences.getPreferences).mockResolvedValue({ counter_collapsed: "true" });
    render(
      <SceneShell
        event={null}
        sessionCostUsd={0}
        beanAlias={null}
        complexity={null}
        hasVisibleContent={false}
        reducedMotion={false}
      />
    );
    await waitFor(() => {
      expect(screen.getByTestId("scene-shell")).toHaveAttribute("data-collapsed", "true");
    });
  });

  it("toggling the chevron flips collapsed state and persists it", async () => {
    render(
      <SceneShell
        event={null}
        sessionCostUsd={0}
        beanAlias={null}
        complexity={null}
        hasVisibleContent={false}
        reducedMotion={false}
      />
    );
    await waitFor(() => expect(preferences.getPreferences).toHaveBeenCalled());

    fireEvent.click(screen.getByTestId("scene-collapse-toggle"));

    expect(screen.getByTestId("scene-shell")).toHaveAttribute("data-collapsed", "true");
    await waitFor(() => {
      expect(preferences.setPreference).toHaveBeenCalledWith("counter_collapsed", "true");
    });
  });

  it("passes paused=true to BaristaScene while collapsed", async () => {
    vi.mocked(preferences.getPreferences).mockResolvedValue({ counter_collapsed: "true" });
    render(
      <SceneShell
        event={null}
        sessionCostUsd={0}
        beanAlias={null}
        complexity={null}
        hasVisibleContent={false}
        reducedMotion={false}
      />
    );
    await waitFor(() => {
      expect(lastBaristaSceneProps?.paused).toBe(true);
    });
  });

  it("passes paused=false to BaristaScene while expanded", async () => {
    render(
      <SceneShell
        event={null}
        sessionCostUsd={0}
        beanAlias={null}
        complexity={null}
        hasVisibleContent={false}
        reducedMotion={false}
      />
    );
    await waitFor(() => {
      expect(lastBaristaSceneProps?.paused).toBe(false);
    });
  });

  it("shows the plain Tips Jar total (no coin animation) in the collapsed strip", async () => {
    vi.mocked(preferences.getPreferences).mockResolvedValue({ counter_collapsed: "true" });
    render(
      <SceneShell
        event={null}
        sessionCostUsd={1.5}
        beanAlias={null}
        complexity={null}
        hasVisibleContent={false}
        reducedMotion={false}
      />
    );
    await waitFor(() => {
      expect(screen.getByTestId("tips-jar-total")).toHaveTextContent("$1.5000");
    });
    expect(screen.queryByTestId("tips-jar-coin")).not.toBeInTheDocument();
  });

  it("shows the collapsed steam indicator only while brewing", async () => {
    vi.mocked(preferences.getPreferences).mockResolvedValue({ counter_collapsed: "true" });
    const { rerender } = render(
      <SceneShell
        event={null}
        sessionCostUsd={0}
        beanAlias={null}
        complexity={null}
        hasVisibleContent={false}
        reducedMotion={false}
      />
    );
    await waitFor(() => expect(preferences.getPreferences).toHaveBeenCalled());
    expect(screen.queryByTestId("scene-collapsed-steam")).not.toBeInTheDocument();

    rerender(
      <SceneShell
        event={generatingEvent("t1")}
        sessionCostUsd={0}
        beanAlias="House Blend"
        complexity="espresso_shot"
        hasVisibleContent={false}
        reducedMotion={false}
      />
    );
    expect(screen.getByTestId("scene-collapsed-steam")).toBeInTheDocument();
  });

  it("renders the status caption from statusText.ts, reused verbatim", () => {
    render(
      <SceneShell
        event={null}
        sessionCostUsd={0}
        beanAlias={null}
        complexity={null}
        hasVisibleContent={false}
        reducedMotion={false}
      />
    );
    expect(screen.getByTestId("scene-caption")).toHaveTextContent("Ready when you are");
  });
});
