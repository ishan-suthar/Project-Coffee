import "@testing-library/jest-dom/vitest";
import { afterEach } from "vitest";
import { cleanup } from "@testing-library/react";

// @testing-library/react does not auto-cleanup under Vitest the way it
// does under Jest globals - without this, elements from earlier tests in
// the same file remain in the DOM and cause "multiple elements found"
// errors in later tests.
afterEach(() => {
  cleanup();
});

// jsdom does not implement window.matchMedia - default stub reports
// "no reduced motion" so any component reading prefers-reduced-motion
// (CounterDisplay/index.tsx, Brew 39) doesn't crash. Tests exercising a
// specific media query result override this per-test via
// vi.spyOn(window, "matchMedia").
if (typeof window !== "undefined" && !window.matchMedia) {
  window.matchMedia = (query: string) =>
    ({
      matches: false,
      media: query,
      onchange: null,
      addListener: () => {},
      removeListener: () => {},
      addEventListener: () => {},
      removeEventListener: () => {},
      dispatchEvent: () => false,
    }) as MediaQueryList;
}
