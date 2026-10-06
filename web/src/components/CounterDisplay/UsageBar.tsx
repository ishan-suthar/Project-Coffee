"use client";

import { useEffect, useState } from "react";
import type { RouterEvent } from "@/lib/events";
import { getUsage, type UsageInfo } from "@/lib/api";
import { usageBarLevel } from "@/components/CounterDisplay/usageBarMath";

interface UsageBarProps {
  /** Latest SSE event - used only to detect a new `complete` to refetch
   * usage after, never to derive the numbers shown. */
  event: RouterEvent | null;
}

const LEVEL_CLASSES: Record<string, string> = {
  normal: "text-medium-roast",
  warning: "text-crema-amber",
  critical: "text-red-700",
};

/** Today's spend against the current user's daily cap - GET /v1/usage,
 * never computed client-side (the router's cap enforcement is the only
 * source of truth for this number). Renders nothing until the first
 * fetch resolves - no placeholder/loading flash for a value this small. */
export function UsageBar({ event }: UsageBarProps) {
  const [usage, setUsage] = useState<UsageInfo | null>(null);

  useEffect(() => {
    getUsage()
      .then(setUsage)
      .catch(() => {
        // Router unreachable, or the account predates this endpoint's
        // deploy - fail silent, same precedent as the preferences fetch.
      });
  }, []);

  useEffect(() => {
    if (event === null || event.event !== "complete") return;
    getUsage()
      .then(setUsage)
      .catch(() => {});
  }, [event]);

  if (usage === null) return null;

  const level = usageBarLevel(usage.todaySpendUsd, usage.capUsd);

  return (
    <div
      data-testid="usage-bar"
      data-level={level}
      className={`font-mono text-xs tabular-nums ${LEVEL_CLASSES[level]}`}
      title="Today's spend against your daily cap"
    >
      <span data-testid="usage-bar-text">
        ${usage.todaySpendUsd.toFixed(2)} of ${usage.capUsd.toFixed(2)} today
      </span>
    </div>
  );
}
