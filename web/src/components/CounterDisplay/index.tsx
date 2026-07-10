import type { CounterDisplayProps } from "@/components/CounterDisplay/types";
import { statusTextFor } from "@/components/CounterDisplay/statusText";

export type { CounterDisplayProps } from "@/components/CounterDisplay/types";

/**
 * Plain-text status line standing in for the future animated scene
 * (Stage E). Everything below is private to this module - callers only
 * ever see CounterDisplayProps (types.ts). Do not import statusTextFor or
 * any other internal from outside this directory.
 */
export function CounterDisplay({ event, sessionCostUsd }: CounterDisplayProps) {
  const statusText = statusTextFor(event);

  return (
    <div
      data-testid="counter-display"
      className="flex items-center justify-between border-b border-caramel bg-latte px-4 py-2"
    >
      <span data-testid="counter-display-status" className="text-sm text-espresso">
        {statusText}
      </span>
      <span
        data-testid="counter-display-tips-jar"
        className="font-mono text-sm tabular-nums text-medium-roast"
        title="Tips Jar - running cost for the active message"
      >
        Tips Jar: ${sessionCostUsd.toFixed(4)}
      </span>
    </div>
  );
}
