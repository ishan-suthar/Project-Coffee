/**
 * Pure coin-drop throttling logic for the Tips Jar (docs/design/
 * counter-scene-design.md Section 3.2 / Requirement 2). Kept separate
 * from TipsJar.tsx so the throttle math is testable without fake timers
 * or a mounted component - the component just calls this on every
 * `generating` tick it receives.
 */

const DEFAULT_THROTTLE_MS = 500;

export interface CoinDropState {
  /** Wall-clock ms of the last coin drop, or null if none has dropped yet. */
  lastCoinAtMs: number | null;
}

export const INITIAL_COIN_DROP_STATE: CoinDropState = { lastCoinAtMs: null };

/** True if enough time has passed since the last coin to drop another
 * one - at most one coin per throttleMs, per Requirement 2. */
export function shouldDropCoin(
  state: CoinDropState,
  nowMs: number,
  throttleMs: number = DEFAULT_THROTTLE_MS
): boolean {
  if (state.lastCoinAtMs === null) return true;
  return nowMs - state.lastCoinAtMs >= throttleMs;
}

/** Returns the next CoinDropState after a drop decision at nowMs -
 * unchanged if shouldDropCoin(state, nowMs) was false, so callers can
 * unconditionally call this and trust it to no-op correctly. */
export function recordCoinDrop(
  state: CoinDropState,
  nowMs: number,
  throttleMs: number = DEFAULT_THROTTLE_MS
): CoinDropState {
  if (!shouldDropCoin(state, nowMs, throttleMs)) return state;
  return { lastCoinAtMs: nowMs };
}
