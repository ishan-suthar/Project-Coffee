import { describe, expect, it } from "vitest";
import {
  INITIAL_COIN_DROP_STATE,
  recordCoinDrop,
  shouldDropCoin,
} from "@/components/CounterDisplay/tipsJarMath";

describe("shouldDropCoin", () => {
  it("allows the very first coin", () => {
    expect(shouldDropCoin(INITIAL_COIN_DROP_STATE, 1000)).toBe(true);
  });

  it("blocks a second coin dropped immediately after the first", () => {
    const afterFirst = recordCoinDrop(INITIAL_COIN_DROP_STATE, 1000);
    expect(shouldDropCoin(afterFirst, 1000)).toBe(false);
    expect(shouldDropCoin(afterFirst, 1200)).toBe(false);
  });

  it("blocks a coin at 499ms since the last one", () => {
    const afterFirst = recordCoinDrop(INITIAL_COIN_DROP_STATE, 1000);
    expect(shouldDropCoin(afterFirst, 1499)).toBe(false);
  });

  it("allows a coin at exactly 500ms since the last one", () => {
    const afterFirst = recordCoinDrop(INITIAL_COIN_DROP_STATE, 1000);
    expect(shouldDropCoin(afterFirst, 1500)).toBe(true);
  });

  it("allows a coin comfortably after the throttle window", () => {
    const afterFirst = recordCoinDrop(INITIAL_COIN_DROP_STATE, 1000);
    expect(shouldDropCoin(afterFirst, 5000)).toBe(true);
  });

  it("respects a custom throttle window", () => {
    const afterFirst = recordCoinDrop(INITIAL_COIN_DROP_STATE, 1000, 1000);
    expect(shouldDropCoin(afterFirst, 1500, 1000)).toBe(false);
    expect(shouldDropCoin(afterFirst, 2000, 1000)).toBe(true);
  });
});

describe("recordCoinDrop", () => {
  it("updates lastCoinAtMs when a drop is allowed", () => {
    const next = recordCoinDrop(INITIAL_COIN_DROP_STATE, 1000);
    expect(next.lastCoinAtMs).toBe(1000);
  });

  it("does not update lastCoinAtMs when throttled - repeated rapid ticks accumulate no more than one coin per window", () => {
    let state = recordCoinDrop(INITIAL_COIN_DROP_STATE, 1000);
    state = recordCoinDrop(state, 1050);
    state = recordCoinDrop(state, 1100);
    state = recordCoinDrop(state, 1400);
    expect(state.lastCoinAtMs).toBe(1000);

    state = recordCoinDrop(state, 1500);
    expect(state.lastCoinAtMs).toBe(1500);
  });

  it("a burst of ten ticks within one throttle window drops exactly one coin", () => {
    let state = INITIAL_COIN_DROP_STATE;
    let dropCount = 0;
    for (let i = 0; i < 10; i += 1) {
      const now = 1000 + i * 40; // ten ticks across 360ms, well under 500ms
      if (shouldDropCoin(state, now)) {
        dropCount += 1;
        state = recordCoinDrop(state, now);
      }
    }
    expect(dropCount).toBe(1);
  });
});
