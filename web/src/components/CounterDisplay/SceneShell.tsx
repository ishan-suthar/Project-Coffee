"use client";

import { useEffect, useState } from "react";
import type { Complexity, RouterEvent } from "@/lib/events";
import { statusTextFor } from "@/components/CounterDisplay/statusText";
import { BaristaScene } from "@/components/CounterDisplay/BaristaScene";
import { TipsJar } from "@/components/CounterDisplay/TipsJar";
import {
  jarBooleansFor,
  machineFor,
  sceneStateIndexFor,
  type SceneStateIndex,
} from "@/components/CounterDisplay/sceneState";
import { getPreferences, setPreference } from "@/lib/preferences";

const COLLAPSE_PREFERENCE_KEY = "counter_collapsed";
// Requirement 4: cup placement and the first response tokens should land
// together; if tokens arrived early, buffer at most 300ms to sync, never
// longer.
const COMPLETE_SYNC_BUFFER_MS = 300;

interface SceneShellProps {
  event: RouterEvent | null;
  sessionCostUsd: number;
  beanAlias: string | null;
  complexity: Complexity | null;
  hasVisibleContent: boolean;
  reducedMotion: boolean;
}

/** Holds the visual "complete" (state 7) transition for up to
 * COMPLETE_SYNC_BUFFER_MS if streamed content hasn't rendered anything
 * yet, resolving the instant hasVisibleContent flips true rather than
 * always waiting the full window - every other state applies
 * immediately, unbuffered. */
function useBufferedSceneState(
  rawSceneState: SceneStateIndex,
  hasVisibleContent: boolean
): SceneStateIndex {
  const [displayState, setDisplayState] = useState(rawSceneState);

  useEffect(() => {
    function applyState(nextState: SceneStateIndex) {
      setDisplayState(nextState);
    }
    if (rawSceneState !== 7 || hasVisibleContent) {
      applyState(rawSceneState);
      return;
    }
    const timeout = window.setTimeout(() => applyState(7), COMPLETE_SYNC_BUFFER_MS);
    return () => clearTimeout(timeout);
  }, [rawSceneState, hasVisibleContent]);

  return displayState;
}

export function SceneShell({
  event,
  sessionCostUsd,
  beanAlias,
  complexity,
  hasVisibleContent,
  reducedMotion,
}: SceneShellProps) {
  const [collapsed, setCollapsed] = useState(false);

  useEffect(() => {
    getPreferences()
      .then((prefs) => {
        if (prefs[COLLAPSE_PREFERENCE_KEY] === "true") setCollapsed(true);
      })
      .catch(() => {
        // Router unreachable or no stored preference yet - default expanded.
      });
  }, []);

  function toggleCollapsed() {
    const next = !collapsed;
    setCollapsed(next);
    setPreference(COLLAPSE_PREFERENCE_KEY, String(next)).catch(() => {
      // Best-effort persistence - the toggle still works locally this session.
    });
  }

  const rawSceneState = sceneStateIndexFor(event);
  const sceneState = useBufferedSceneState(rawSceneState, hasVisibleContent);
  const jarBooleans = jarBooleansFor(sceneState, beanAlias);
  const machine = machineFor(sceneState, complexity);
  const caption = statusTextFor(event);
  const isBrewing = sceneState === 4;

  return (
    <div
      className="relative border-b border-caramel bg-latte"
      data-testid="scene-shell"
      data-collapsed={collapsed}
    >
      <div className="flex items-center justify-between px-4 py-2">
        <button
          type="button"
          onClick={toggleCollapsed}
          aria-label={collapsed ? "Expand the Coffee Counter scene" : "Collapse the Coffee Counter scene"}
          data-testid="scene-collapse-toggle"
          className={`text-espresso transition-transform ${collapsed ? "rotate-180" : ""}`}
        >
          {/* eslint-disable-next-line @next/next/no-img-element -- static local icon */}
          <img src="/assets/icons/chevron_collapse.svg" alt="" className="h-4 w-4" aria-hidden="true" />
        </button>

        <span data-testid="scene-caption" className="text-sm text-espresso">
          {caption}
        </span>

        {collapsed ? (
          <span
            data-testid="tips-jar-total"
            className="font-mono text-sm tabular-nums text-medium-roast"
            title="Tips Jar - running cost for the active message"
          >
            ${sessionCostUsd.toFixed(4)}
          </span>
        ) : (
          <TipsJar sessionCostUsd={sessionCostUsd} event={event} />
        )}
      </div>

      {collapsed && isBrewing && (
        // eslint-disable-next-line @next/next/no-img-element -- static local icon
        <img
          src="/assets/icons/steam.svg"
          alt=""
          data-testid="scene-collapsed-steam"
          className="absolute left-1/2 top-1 h-4 w-4 -translate-x-1/2"
          aria-hidden="true"
        />
      )}

      <div className={collapsed ? "h-0 overflow-hidden" : "h-32"} data-testid="scene-body">
        <BaristaScene
          sceneState={sceneState}
          jarBooleans={jarBooleans}
          machine={machine}
          reducedMotion={reducedMotion}
          paused={collapsed}
        />
        {!collapsed && (
          <div
            className="pointer-events-none absolute inset-x-0 bottom-0 h-8 bg-gradient-to-b from-transparent to-cream"
            aria-hidden="true"
          />
        )}
      </div>
    </div>
  );
}
