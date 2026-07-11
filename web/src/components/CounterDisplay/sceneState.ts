import type { Complexity, RouterEvent } from "@/lib/events";

/**
 * Pure event-to-scene mappings for the animated Coffee Counter (Stage E -
 * docs/design/counter-scene-design.md). Every function here is a pure
 * function of its arguments - no history, no memory of prior events, no
 * client-side inference of pipeline state. The three fields these
 * functions need beyond the latest event (bean alias, complexity,
 * whether content has rendered) are carried forward by the caller
 * (web/src/app/page.tsx) from data it already tracks per message - see
 * CounterDisplayProps in types.ts - never re-derived or guessed here.
 */

export type SceneStateIndex = 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8;

export type MachineKind = "espresso" | "pour_over" | null;

/** Matches router/config/beans.yaml's real aliases exactly, plus a spare
 * fallback for any future alias without dedicated jar art yet - see
 * public/assets/counter/README.md for why there is no roast-themed jar
 * set. */
export type JarKey =
  | "jar_house_blend"
  | "jar_second_pour"
  | "jar_guest_bean"
  | "jar_reserve_blend"
  | "jar_default";

export const JAR_KEYS: readonly JarKey[] = [
  "jar_house_blend",
  "jar_second_pour",
  "jar_guest_bean",
  "jar_reserve_blend",
  "jar_default",
];

const ALIAS_TO_JAR_KEY: Record<string, JarKey> = {
  "House Blend": "jar_house_blend",
  "Second Pour": "jar_second_pour",
  "Guest Bean": "jar_guest_bean",
  "Reserve Blend": "jar_reserve_blend",
};

/** 0 idle, 1 order_received, 2 classifying, 3 route_selected,
 * 4 generating, 5 escalation_pending, 6 escalating, 7 complete,
 * 8 error. `cancelled` reuses 8's art with a different caption
 * (statusText.ts already provides the distinct wording) - not a 9th
 * state, matching the CounterFlow state machine's input range. */
export function sceneStateIndexFor(event: RouterEvent | null): SceneStateIndex {
  if (event === null) return 0;
  switch (event.event) {
    case "order_received":
      return 1;
    case "classifying":
      return 2;
    case "route_selected":
      return 3;
    case "generating":
      return 4;
    case "escalation_pending":
      return 5;
    case "escalating":
      return 6;
    case "complete":
      return 7;
    case "error":
      return 8;
    case "cancelled":
      return 8;
  }
}

/** null for an alias with no dedicated jar (never happens for a real
 * router response today, since every bean_alias is one of the four
 * known aliases) - "jar_default" for an alias this scene doesn't
 * recognize, rather than silently highlighting nothing or guessing. */
export function jarKeyFor(beanAlias: string | null): JarKey | null {
  if (beanAlias === null) return null;
  return ALIAS_TO_JAR_KEY[beanAlias] ?? "jar_default";
}

/** Exactly one true during states 3 (route_selected) and 4 (generating),
 * per the CounterFlow spec - false for every key otherwise, including
 * when beanAlias is null (no route chosen yet). */
export function jarBooleansFor(
  sceneState: SceneStateIndex,
  beanAlias: string | null
): Record<JarKey, boolean> {
  const activeKey = sceneState === 3 || sceneState === 4 ? jarKeyFor(beanAlias) : null;
  const result = {} as Record<JarKey, boolean>;
  for (const key of JAR_KEYS) {
    result[key] = key === activeKey;
  }
  return result;
}

/** Machine only appears during state 4 (generating). complexity === null
 * during state 4 should not happen in practice (route_selected always
 * precedes generating and always carries complexity), but if it ever
 * does, this returns null rather than guessing which machine to show. */
export function machineFor(sceneState: SceneStateIndex, complexity: Complexity | null): MachineKind {
  if (sceneState !== 4) return null;
  if (complexity === "cold_brew") return "pour_over";
  if (complexity === "espresso_shot") return "espresso";
  return null;
}
