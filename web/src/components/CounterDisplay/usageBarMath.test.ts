import { describe, expect, it } from "vitest";
import { usageBarLevel } from "@/components/CounterDisplay/usageBarMath";

describe("usageBarLevel", () => {
  it("is normal well under the cap", () => {
    expect(usageBarLevel(0.1, 1.0)).toBe("normal");
  });

  it("is normal just under the 80% warning threshold", () => {
    expect(usageBarLevel(0.79, 1.0)).toBe("normal");
  });

  it("is warning at exactly 80% of the cap", () => {
    expect(usageBarLevel(0.8, 1.0)).toBe("warning");
  });

  it("is warning between 80% and 100%", () => {
    expect(usageBarLevel(0.95, 1.0)).toBe("warning");
  });

  it("is critical at exactly the cap", () => {
    expect(usageBarLevel(1.0, 1.0)).toBe("critical");
  });

  it("is critical over the cap", () => {
    expect(usageBarLevel(1.5, 1.0)).toBe("critical");
  });

  it("is normal at zero spend", () => {
    expect(usageBarLevel(0, 1.0)).toBe("normal");
  });

  it("treats a zero cap as critical the moment there is any spend", () => {
    expect(usageBarLevel(0.01, 0)).toBe("critical");
  });

  it("treats a zero cap with zero spend as normal, never divides by zero", () => {
    expect(usageBarLevel(0, 0)).toBe("normal");
  });
});
