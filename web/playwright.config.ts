import { defineConfig, devices } from "@playwright/test";

/**
 * The Playwright smoke test mocks the Coffee Core Router's HTTP surface
 * via page.route() (see e2e/chat.spec.ts) - it never makes a live
 * OpenRouter call and never requires OPENROUTER_API_KEY, matching the
 * router's own "no live network calls in automated tests" discipline
 * (router/tests/). The real live demo (a human watching a real /v1/order
 * call) is a separate, manual step - see docs/design/
 * coffee-counter-chat-ui-design.md Section 13.
 */
export default defineConfig({
  testDir: "./e2e",
  timeout: 30_000,
  fullyParallel: true,
  retries: 0,
  reporter: "list",
  use: {
    baseURL: "http://127.0.0.1:3100",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer: {
    // Build ahead of time (see e2e test-running instructions in
    // router/README.md-equivalent docs) - a single `next start -p 3100`
    // command is more reliable to spawn/detect across shells than a
    // chained `npm run build && npm run start -- --port`.
    command: "npx next start -p 3100",
    url: "http://127.0.0.1:3100",
    reuseExistingServer: false,
    timeout: 60_000,
  },
});
