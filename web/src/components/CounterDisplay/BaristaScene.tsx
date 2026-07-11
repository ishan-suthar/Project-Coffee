"use client";

import { useEffect, useMemo, useState } from "react";
import { useRive, useStateMachineInput } from "@rive-app/react-canvas";
import { JAR_KEYS, type JarKey, type MachineKind, type SceneStateIndex } from "@/components/CounterDisplay/sceneState";

const RIVE_SRC = "/assets/counter/barista_scene.riv";
const FALLBACK_SRC = "/assets/counter/barista_static.svg";
const STATE_MACHINE_NAME = "CounterFlow";

interface BaristaSceneProps {
  sceneState: SceneStateIndex;
  jarBooleans: Record<JarKey, boolean>;
  machine: MachineKind;
  /** prefers-reduced-motion: reduce - Rive is never even attempted, per
   * Requirement 5. */
  reducedMotion: boolean;
  /** Collapsed - must actually pause the Rive state machine (rive.pause()),
   * not just hide the canvas, per Requirement 3 / Section 6's "near-zero
   * CPU" requirement. */
  paused: boolean;
}

type LoadState = "idle" | "loaded" | "error";

/**
 * Tier 1 (Rive) / tier 2 (barista_static.svg) fallback ladder - see
 * docs/design/counter-scene-design.md Section 3. barista_scene.riv is
 * always attempted (lazily, after first paint); the moment a real file
 * exists at RIVE_SRC and loads successfully, tier 1 takes over with zero
 * code changes. Today (Phase 1, no real .riv committed) onLoadError
 * always fires and tier 2 renders - this is the same code path
 * Requirement 5's reduced-motion/load-failure fallback specifies, not a
 * separate throwaway implementation.
 */
export function BaristaScene({ sceneState, jarBooleans, machine, reducedMotion, paused }: BaristaSceneProps) {
  const [mountRive, setMountRive] = useState(false);
  const [loadState, setLoadState] = useState<LoadState>("idle");

  useEffect(() => {
    if (reducedMotion) return;
    // Lazy-load after first paint (Requirement 6) rather than blocking
    // the scene's own initial render on the Rive asset.
    const frame = requestAnimationFrame(() => setMountRive(true));
    return () => cancelAnimationFrame(frame);
  }, [reducedMotion]);

  // Memoized so the params object identity is stable across re-renders
  // (e.g. every sceneState change) - avoids reinitializing the Rive
  // instance on unrelated prop updates.
  const riveParams = useMemo(
    () =>
      mountRive && !reducedMotion
        ? {
            src: RIVE_SRC,
            stateMachines: STATE_MACHINE_NAME,
            autoplay: true,
            onLoad: () => setLoadState("loaded"),
            onLoadError: () => setLoadState("error"),
          }
        : null,
    [mountRive, reducedMotion]
  );

  const { rive, RiveComponent } = useRive(riveParams, { shouldResizeCanvasToContainer: true });

  const stateInput = useStateMachineInput(rive, STATE_MACHINE_NAME, "state");
  const jarHouseBlendInput = useStateMachineInput(rive, STATE_MACHINE_NAME, "jar_house_blend");
  const jarSecondPourInput = useStateMachineInput(rive, STATE_MACHINE_NAME, "jar_second_pour");
  const jarGuestBeanInput = useStateMachineInput(rive, STATE_MACHINE_NAME, "jar_guest_bean");
  const jarReserveBlendInput = useStateMachineInput(rive, STATE_MACHINE_NAME, "jar_reserve_blend");
  const jarDefaultInput = useStateMachineInput(rive, STATE_MACHINE_NAME, "jar_default");
  const complexityInput = useStateMachineInput(rive, STATE_MACHINE_NAME, "complexity_cold_brew");

  useEffect(() => {
    // Rive's StateMachineInput.value is an imperative setter on the
    // runtime's own object, not React state - this is the documented way
    // to drive it (@rive-app/react-canvas useStateMachineInput), not an
    // accidental mutation of a hook's return value.
    // eslint-disable-next-line react-hooks/immutability
    if (stateInput) stateInput.value = sceneState;
  }, [stateInput, sceneState]);

  useEffect(() => {
    const inputsByKey: Record<JarKey, typeof jarHouseBlendInput> = {
      jar_house_blend: jarHouseBlendInput,
      jar_second_pour: jarSecondPourInput,
      jar_guest_bean: jarGuestBeanInput,
      jar_reserve_blend: jarReserveBlendInput,
      jar_default: jarDefaultInput,
    };
    for (const key of JAR_KEYS) {
      const input = inputsByKey[key];
      if (input) input.value = jarBooleans[key];
    }
  }, [jarHouseBlendInput, jarSecondPourInput, jarGuestBeanInput, jarReserveBlendInput, jarDefaultInput, jarBooleans]);

  useEffect(() => {
    // Same imperative Rive setter as above, not React state.
    // eslint-disable-next-line react-hooks/immutability
    if (complexityInput) complexityInput.value = machine === "pour_over";
  }, [complexityInput, machine]);

  useEffect(() => {
    if (!rive) return;
    if (paused) rive.pause();
    else rive.play();
  }, [rive, paused]);

  const showRive = !reducedMotion && loadState === "loaded";

  return (
    <div data-testid="barista-scene" className="relative h-32 w-full overflow-hidden">
      {showRive ? (
        <RiveComponent data-testid="barista-scene-rive" className="h-full w-full" />
      ) : (
        // eslint-disable-next-line @next/next/no-img-element -- static local placeholder/fallback art, not an optimizable remote image
        <img
          src={FALLBACK_SRC}
          alt="Coffee counter scene"
          data-testid="barista-scene-fallback"
          className="h-full w-full object-contain"
        />
      )}
    </div>
  );
}
