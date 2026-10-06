/**
 * Pure threshold logic for the daily-spend usage bar (spend-cap Brew).
 * Kept separate from UsageBar.tsx so the amber/red thresholds are
 * testable without a mounted component - same precedent as
 * tipsJarMath.ts's coin-drop throttle logic.
 */

export type UsageBarLevel = "normal" | "warning" | "critical";

const WARNING_FRACTION = 0.8;

/** "critical" at/over the cap, "warning" at/over 80% of it, "normal"
 * otherwise. capUsd <= 0 is treated as critical the moment there is any
 * spend at all (a $0 cap has already been reached by definition) rather
 * than dividing by zero. */
export function usageBarLevel(todaySpendUsd: number, capUsd: number): UsageBarLevel {
  if (capUsd <= 0) return todaySpendUsd > 0 ? "critical" : "normal";
  const fraction = todaySpendUsd / capUsd;
  if (fraction >= 1) return "critical";
  if (fraction >= WARNING_FRACTION) return "warning";
  return "normal";
}
