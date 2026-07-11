"use client";

import { useEffect, useRef, useState } from "react";
import type { RouterEvent } from "@/lib/events";
import { INITIAL_COIN_DROP_STATE, recordCoinDrop, shouldDropCoin } from "@/components/CounterDisplay/tipsJarMath";

interface TipsJarProps {
  /** Running total for the active message - persists as-is until the
   * caller resets it on the next order_received (page.tsx's existing
   * derivation), not reset internally by this component. */
  sessionCostUsd: number;
  /** Latest SSE event, used only to detect a new `generating` tick to
   * throttle-drop a coin for - never to derive cost or state. */
  event: RouterEvent | null;
}

let coinIdSeq = 0;

export function TipsJar({ sessionCostUsd, event }: TipsJarProps) {
  const [coins, setCoins] = useState<number[]>([]);
  const coinDropStateRef = useRef(INITIAL_COIN_DROP_STATE);
  const lastHandledEventTsRef = useRef<string | null>(null);

  useEffect(() => {
    if (event === null || event.event !== "generating") return;
    if (event.ts === lastHandledEventTsRef.current) return;
    lastHandledEventTsRef.current = event.ts;

    const now = Date.now();
    if (!shouldDropCoin(coinDropStateRef.current, now)) return;
    coinDropStateRef.current = recordCoinDrop(coinDropStateRef.current, now);

    coinIdSeq += 1;
    const id = coinIdSeq;
    setCoins((prev) => [...prev, id]);
    setTimeout(() => {
      setCoins((prev) => prev.filter((coinId) => coinId !== id));
    }, 650);
  }, [event]);

  return (
    <div
      data-testid="tips-jar"
      className="relative flex items-center gap-2 font-mono text-sm tabular-nums text-medium-roast"
      title="Tips Jar - running cost for the active message"
    >
      <span className="relative">
        {/* eslint-disable-next-line @next/next/no-img-element -- static local placeholder art, not an optimizable remote/content image */}
        <img src="/assets/counter/tips_jar.svg" alt="" className="h-8 w-8" aria-hidden="true" />
        {coins.map((id) => (
          <span
            key={id}
            data-testid="tips-jar-coin"
            className="coin-drop pointer-events-none absolute left-1/2 top-0 h-2 w-2 -translate-x-1/2 rounded-full bg-crema-amber"
          />
        ))}
      </span>
      <span data-testid="tips-jar-total">Tips Jar: ${sessionCostUsd.toFixed(4)}</span>
    </div>
  );
}
