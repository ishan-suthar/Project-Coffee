import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import React from "react";
import { BaristaScene } from "@/components/CounterDisplay/BaristaScene";
import { jarBooleansFor } from "@/components/CounterDisplay/sceneState";

/**
 * @rive-app/react-canvas needs a real WASM/canvas context jsdom can't
 * provide, so it's mocked here the same way router requests are mocked
 * in other component tests (e.g. AttachmentChip.test.tsx mocks
 * @/lib/api) - this fakes the async load lifecycle (onLoad/onLoadError
 * fired from an effect, matching real Rive's async behavior) and a
 * controllable rive instance so pause()/play() calls are assertable.
 */
const riveMock = vi.hoisted(() => ({
  shouldSucceed: true,
  lastInstance: null as null | { pause: ReturnType<typeof vi.fn>; play: ReturnType<typeof vi.fn> },
  inputs: {} as Record<string, { value: number | boolean }>,
}));

vi.mock("@rive-app/react-canvas", () => {
  return {
    useRive: (params: { src?: string; onLoad?: () => void; onLoadError?: () => void } | null) => {
      const [riveInstance, setRiveInstance] = React.useState<typeof riveMock.lastInstance>(null);
      const hasParams = !!params;
      React.useEffect(() => {
        if (!params) return;
        if (riveMock.shouldSucceed) {
          const instance = { pause: vi.fn(), play: vi.fn() };
          riveMock.lastInstance = instance;
          setRiveInstance(instance);
          params.onLoad?.();
        } else {
          params.onLoadError?.();
        }
        // Depend on whether params is present, not the object's identity -
        // a fresh literal every render must not re-trigger this (the same
        // reasoning the real useRive applies internally: it depends on
        // !!riveParams, not riveParams itself).
        // eslint-disable-next-line react-hooks/exhaustive-deps
      }, [hasParams]);

      function RiveComponent(props: Record<string, unknown>) {
        return React.createElement("div", { ...props, "data-testid": "mock-rive-canvas" });
      }

      return { rive: riveInstance, RiveComponent };
    },
    useStateMachineInput: (rive: unknown, _stateMachine: string, name?: string) => {
      if (!rive || !name) return null;
      if (!riveMock.inputs[name]) riveMock.inputs[name] = { value: 0 };
      return riveMock.inputs[name];
    },
  };
});

const NO_JARS = jarBooleansFor(0, null);

describe("BaristaScene", () => {
  beforeEach(() => {
    riveMock.shouldSucceed = true;
    riveMock.lastInstance = null;
    riveMock.inputs = {};
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders the barista_static.svg fallback under prefers-reduced-motion, never attempting Rive", async () => {
    render(
      <BaristaScene sceneState={0} jarBooleans={NO_JARS} machine={null} reducedMotion paused={false} />
    );
    expect(screen.getByTestId("barista-scene-fallback")).toHaveAttribute(
      "src",
      "/assets/counter/barista_static.svg"
    );
    expect(screen.queryByTestId("mock-rive-canvas")).not.toBeInTheDocument();
  });

  it("renders the fallback when the Rive file fails to load (missing today)", async () => {
    riveMock.shouldSucceed = false;
    render(
      <BaristaScene sceneState={0} jarBooleans={NO_JARS} machine={null} reducedMotion={false} paused={false} />
    );
    await waitFor(() => {
      expect(screen.getByTestId("barista-scene-fallback")).toBeInTheDocument();
    });
    expect(screen.queryByTestId("mock-rive-canvas")).not.toBeInTheDocument();
  });

  it("renders the Rive canvas once the file loads successfully", async () => {
    render(
      <BaristaScene sceneState={3} jarBooleans={jarBooleansFor(3, "House Blend")} machine={null} reducedMotion={false} paused={false} />
    );
    await waitFor(() => {
      expect(screen.getByTestId("mock-rive-canvas")).toBeInTheDocument();
    });
    expect(screen.queryByTestId("barista-scene-fallback")).not.toBeInTheDocument();
  });

  it("sets the state machine's state input to the given sceneState", async () => {
    render(
      <BaristaScene sceneState={7} jarBooleans={NO_JARS} machine={null} reducedMotion={false} paused={false} />
    );
    await waitFor(() => {
      expect(riveMock.inputs["state"]?.value).toBe(7);
    });
  });

  it("sets exactly one jar boolean input true, matching jarBooleansFor", async () => {
    render(
      <BaristaScene
        sceneState={4}
        jarBooleans={jarBooleansFor(4, "Reserve Blend")}
        machine="espresso"
        reducedMotion={false}
        paused={false}
      />
    );
    await waitFor(() => {
      expect(riveMock.inputs["jar_reserve_blend"]?.value).toBe(true);
    });
    expect(riveMock.inputs["jar_house_blend"]?.value).toBe(false);
    expect(riveMock.inputs["jar_second_pour"]?.value).toBe(false);
    expect(riveMock.inputs["jar_guest_bean"]?.value).toBe(false);
  });

  it("sets complexity_cold_brew true only for the pour-over machine", async () => {
    render(
      <BaristaScene sceneState={4} jarBooleans={NO_JARS} machine="pour_over" reducedMotion={false} paused={false} />
    );
    await waitFor(() => {
      expect(riveMock.inputs["complexity_cold_brew"]?.value).toBe(true);
    });
  });

  it("calls rive.pause() when paused becomes true", async () => {
    const { rerender } = render(
      <BaristaScene sceneState={4} jarBooleans={NO_JARS} machine="espresso" reducedMotion={false} paused={false} />
    );
    await waitFor(() => {
      expect(riveMock.lastInstance).not.toBeNull();
    });
    expect(riveMock.lastInstance?.pause).not.toHaveBeenCalled();

    rerender(
      <BaristaScene sceneState={4} jarBooleans={NO_JARS} machine="espresso" reducedMotion={false} paused />
    );
    await waitFor(() => {
      expect(riveMock.lastInstance?.pause).toHaveBeenCalled();
    });
  });

  it("calls rive.play() when paused becomes false again", async () => {
    const { rerender } = render(
      <BaristaScene sceneState={4} jarBooleans={NO_JARS} machine="espresso" reducedMotion={false} paused />
    );
    await waitFor(() => {
      expect(riveMock.lastInstance).not.toBeNull();
    });

    rerender(
      <BaristaScene sceneState={4} jarBooleans={NO_JARS} machine="espresso" reducedMotion={false} paused={false} />
    );
    await waitFor(() => {
      expect(riveMock.lastInstance?.play).toHaveBeenCalled();
    });
  });
});
