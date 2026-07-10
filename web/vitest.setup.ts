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
