"use client";

import { useEffect } from "react";

/**
 * Sets data-hydrated="true" on <html> once the client has mounted, so
 * globals.css can disable all transitions/animations until then - nothing
 * animates on first paint, only on interaction after hydration.
 * See docs/design/coffee-counter-chat-ui-design.md Section 6.
 */
export function HydrationMarker() {
  useEffect(() => {
    document.documentElement.setAttribute("data-hydrated", "true");
  }, []);

  return null;
}
