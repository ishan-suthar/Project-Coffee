"use client";

import { useEffect, useState } from "react";
import type { CounterDisplayProps } from "@/components/CounterDisplay/types";
import { SceneShell } from "@/components/CounterDisplay/SceneShell";

export type { CounterDisplayProps } from "@/components/CounterDisplay/types";

/**
 * The animated Coffee Counter scene (Stage E, Brew 39 - see
 * docs/design/counter-scene-design.md). Everything below is private to
 * this module - callers only ever see CounterDisplayProps (types.ts).
 * Do not import SceneShell, BaristaScene, sceneState, or any other
 * internal from outside this directory.
 */
export function CounterDisplay({
  event,
  sessionCostUsd,
  beanAlias,
  complexity,
  hasVisibleContent,
}: CounterDisplayProps) {
  // Starts false to match server-rendered HTML exactly (window doesn't
  // exist during SSR - same reasoning as HydrationMarker's "nothing
  // animates before hydration" pattern), then syncs to the real value via
  // the same listener function used for later changes, immediately on
  // mount - not a separate direct setState call in the effect body.
  const [reducedMotion, setReducedMotion] = useState(false);

  useEffect(() => {
    const query = window.matchMedia("(prefers-reduced-motion: reduce)");
    function handleChange(e: MediaQueryListEvent | MediaQueryList) {
      setReducedMotion(e.matches);
    }
    handleChange(query);
    query.addEventListener("change", handleChange as (e: MediaQueryListEvent) => void);
    return () => query.removeEventListener("change", handleChange as (e: MediaQueryListEvent) => void);
  }, []);

  return (
    <SceneShell
      event={event}
      sessionCostUsd={sessionCostUsd}
      beanAlias={beanAlias}
      complexity={complexity}
      hasVisibleContent={hasVisibleContent}
      reducedMotion={reducedMotion}
    />
  );
}
