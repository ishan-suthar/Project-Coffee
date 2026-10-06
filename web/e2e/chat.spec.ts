import { test, expect } from "@playwright/test";

const ROUTER_ORIGIN = "http://127.0.0.1:8765";

const RAW_MODEL_IDS = [
  "nvidia/nemotron-3-ultra-550b-a55b:free",
  "cohere/north-mini-code:free",
  "poolside/laguna-m.1:free",
];

const BEANS = [
  { alias: "House Blend", role: "default", available: true },
  { alias: "Second Pour", role: "fallback", available: true },
  { alias: "Reserve Blend", role: "premium", available: false },
];

function sseBody(): string {
  const events = [
    { event: "order_received", request_id: "req-e2e-1", ts: "2026-07-10T00:00:00Z", prompt_chars: 30 },
    { event: "classifying", request_id: "req-e2e-1", ts: "2026-07-10T00:00:00Z" },
    {
      event: "route_selected",
      request_id: "req-e2e-1",
      ts: "2026-07-10T00:00:00Z",
      bean_alias: "House Blend",
      task_type: "explain",
      complexity: "espresso_shot",
      est_cost_usd: 0,
      policy_entry: "explain/house-blend",
    },
    {
      event: "generating",
      request_id: "req-e2e-1",
      ts: "2026-07-10T00:00:01Z",
      tokens_out: 5,
      est_cost_usd: 0,
      text_delta: "A **decorator** is ",
    },
    {
      event: "generating",
      request_id: "req-e2e-1",
      ts: "2026-07-10T00:00:02Z",
      tokens_out: 10,
      est_cost_usd: 0,
      text_delta: "a function that wraps another function.",
    },
    {
      event: "complete",
      request_id: "req-e2e-1",
      ts: "2026-07-10T00:00:03Z",
      bean_alias: "House Blend",
      tokens_in: 10,
      tokens_out: 15,
      cost_usd: 0,
      latency_ms: 1200,
      escalated: false,
      draft_quality: false,
    },
  ];
  return events.map((e) => `data: ${JSON.stringify(e)}\n\n`).join("");
}

test.beforeEach(async ({ page, context, baseURL }) => {
  // Brew 43 (docs/design/auth-projects-chat-management-design.md): every
  // router call now requires a Bearer token, and Next.js middleware
  // redirects to /login when the token cookie is absent - seed a fake
  // token the same way a real login would, on this frontend's own
  // origin (not the router's), matching how authFetch's plain
  // JS-readable cookie actually works.
  await context.addCookies([
    { name: "coffee_counter_token", value: "e2e-test-token", url: baseURL },
  ]);

  await page.route(`${ROUTER_ORIGIN}/v1/sessions?**`, async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: "[]" });
  });

  await page.route(`${ROUTER_ORIGIN}/v1/sessions`, async (route) => {
    if (route.request().method() !== "POST") return route.continue();
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ id: "test-session-id", project: "default", project_id: null }),
    });
  });

  await page.route(`${ROUTER_ORIGIN}/v1/projects`, async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: "[]" });
  });

  await page.route(`${ROUTER_ORIGIN}/v1/beans`, async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(BEANS) });
  });

  await page.route(`${ROUTER_ORIGIN}/v1/order`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "text/event-stream",
      body: sseBody(),
    });
  });
});

test("send a prompt, see the stream, see the bean badge and cost", async ({ page }) => {
  await page.goto("/");

  await expect(page.getByTestId("scene-caption")).toHaveText("Ready when you are");

  const textarea = page.getByPlaceholder(/Place your order/);
  await textarea.fill("Explain what a Python decorator is.");
  await textarea.press("Enter");

  // The user's message appears immediately.
  await expect(page.getByTestId("user-message")).toContainText("Explain what a Python decorator is.");

  // The assistant message streams in and completes.
  const assistantMessage = page.getByTestId("assistant-message");
  await expect(assistantMessage).toContainText("wraps another function", { timeout: 10_000 });

  // Bean alias badge and cost pill are visible on the completed message.
  await expect(page.getByTestId("bean-alias-badge")).toHaveText("House Blend");
  await expect(page.getByTestId("cost-pill")).toHaveText("$0.0000");

  // Status line returned to "Order up" after complete.
  await expect(page.getByTestId("scene-caption")).toHaveText("Order up");
});

test("web search citation chips render with real hrefs from a populated web_sources", async ({ page }) => {
  // Uses the exact real web_sources shape captured from a live /v1/order
  // call during the citation-fix Brew's demo - a genuine, previously-
  // empty CompleteEvent field, now populated.
  await page.route(`${ROUTER_ORIGIN}/v1/order`, async (route) => {
    const events = [
      { event: "order_received", request_id: "req-e2e-web", ts: "2026-07-18T00:00:00Z", prompt_chars: 40 },
      {
        event: "complete",
        request_id: "req-e2e-web",
        ts: "2026-07-18T00:00:03Z",
        bean_alias: "Kimi K2",
        tokens_in: 21,
        tokens_out: 377,
        cost_usd: 0.005042,
        latency_ms: 13875,
        escalated: false,
        draft_quality: false,
        pantry_sources: null,
        history_turns: null,
        history_tokens_est: null,
        web_sources: [
          {
            url: "https://www.morningstar.com/stocks/best-performing-stocks-quarter",
            title: "Best-Performing Stocks for the Quarter | Morningstar",
          },
          {
            url: "https://csimarket.com/screening/performance.php?days=week",
            title: "This Week's Best Performing Stocks, Sectors, Industries Rankings - CSIMarket",
          },
        ],
      },
    ];
    await route.fulfill({
      status: 200,
      contentType: "text/event-stream",
      body: events.map((e) => `data: ${JSON.stringify(e)}\n\n`).join(""),
    });
  });

  await page.goto("/");
  const textarea = page.getByPlaceholder(/Place your order/);
  await textarea.fill("What are the top performing equities this week?");
  await textarea.press("Enter");

  const chips = page.getByTestId("web-source-chip");
  await expect(chips).toHaveCount(2, { timeout: 10_000 });
  await expect(chips.first()).toHaveText("Best-Performing Stocks for the Quarter | Morningstar");
  await expect(chips.first()).toHaveAttribute(
    "href",
    "https://www.morningstar.com/stocks/best-performing-stocks-quarter"
  );
  await expect(chips.first()).toHaveAttribute("target", "_blank");
});

test("Shift+Enter inserts a newline instead of sending", async ({ page }) => {
  await page.goto("/");
  const textarea = page.getByPlaceholder(/Place your order/);
  await textarea.fill("line one");
  await textarea.press("Shift+Enter");
  await textarea.type("line two");
  await expect(textarea).toHaveValue("line one\nline two");
  await expect(page.getByTestId("user-message")).toHaveCount(0);
});

test("raw model IDs never appear anywhere in the rendered page", async ({ page }) => {
  await page.goto("/");
  const textarea = page.getByPlaceholder(/Place your order/);
  await textarea.fill("Explain what a Python decorator is.");
  await textarea.press("Enter");

  await expect(page.getByTestId("assistant-message")).toContainText("wraps another function", {
    timeout: 10_000,
  });

  const pageText = await page.locator("body").innerText();
  for (const rawId of RAW_MODEL_IDS) {
    expect(pageText).not.toContain(rawId);
  }
});

test("no token cookie redirects to /login, and a successful login redirects back to /", async ({
  page,
  context,
}) => {
  // Override this file's beforeEach seeded cookie - this test is
  // specifically about the no-token/login path.
  await context.clearCookies();

  await page.route(`${ROUTER_ORIGIN}/v1/login`, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        token: "e2e-login-token",
        user: { id: 1, username: "alice", display_name: "Alice" },
      }),
    });
  });

  await page.goto("/");
  await expect(page).toHaveURL(/\/login$/);
  await expect(page.getByText("Sign in to Coffee Counter")).toBeVisible();

  await page.getByLabel("Username").fill("alice");
  await page.getByLabel("Password").fill("hunter2");
  await page.getByRole("button", { name: /sign in/i }).click();

  await expect(page).toHaveURL(/\/$/);
  await expect(page.getByTestId("scene-caption")).toHaveText("Ready when you are");
});

test("the barista panel hides below the 1024px breakpoint, replaced by a text-only status line", async ({
  page,
}) => {
  await page.setViewportSize({ width: 900, height: 800 });
  await page.goto("/");

  await expect(page.getByTestId("scene-shell")).toBeHidden();
  await expect(page.getByTestId("scene-mobile-status")).toBeVisible();
  await expect(page.getByTestId("scene-caption-mobile")).toHaveText("Ready when you are");
});

test("the barista panel is visible at desktop widths, hiding the mobile fallback", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 800 });
  await page.goto("/");

  await expect(page.getByTestId("scene-shell")).toBeVisible();
  await expect(page.getByTestId("scene-mobile-status")).toBeHidden();
});

test("mobile: sidebar is a closed drawer by default, opens via the hamburger, and closes on outside tap", async ({
  page,
}) => {
  await page.setViewportSize({ width: 375, height: 800 });
  await page.goto("/");

  const sidebarSessions = page.getByTestId("sidebar-sessions");
  const hamburger = page.getByTestId("mobile-sidebar-toggle");
  await expect(hamburger).toBeVisible();

  // Closed by default: the drawer is translated off the left edge of the
  // viewport (translate-x-full), not merely display:none - assert on its
  // real position rather than toBeVisible(), which does not account for
  // an off-screen transform.
  const closedBox = await sidebarSessions.boundingBox();
  expect(closedBox).not.toBeNull();
  expect(closedBox!.x).toBeLessThan(0);

  await hamburger.click();
  await expect(page.getByTestId("sidebar-mobile-overlay")).toBeVisible();
  // The drawer slides in over a 200ms CSS transition - poll until it
  // finishes rather than racing a single boundingBox() read against it.
  await expect
    .poll(async () => (await sidebarSessions.boundingBox())?.x ?? -1)
    .toBeGreaterThanOrEqual(0);

  // Tapping the backdrop overlay closes the drawer again.
  await page.getByTestId("sidebar-mobile-overlay").click({ position: { x: 350, y: 10 } });
  await expect(page.getByTestId("sidebar-mobile-overlay")).toBeHidden();
  await expect
    .poll(async () => (await sidebarSessions.boundingBox())?.x ?? 0)
    .toBeLessThan(0);
});

test("mobile: no horizontal scrolling, and the barista panel/CounterDisplay is hidden", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 800 });
  await page.goto("/");

  await expect(page.getByTestId("scene-shell")).toBeHidden();

  const hasHorizontalOverflow = await page.evaluate(
    () => document.documentElement.scrollWidth > document.documentElement.clientWidth
  );
  expect(hasHorizontalOverflow).toBe(false);
});

test("desktop: the mobile hamburger is not rendered and the sidebar is in its normal static position", async ({
  page,
}) => {
  await page.setViewportSize({ width: 1280, height: 800 });
  await page.goto("/");

  await expect(page.getByTestId("mobile-sidebar-toggle")).toBeHidden();
  const sidebarSessions = page.getByTestId("sidebar-sessions");
  const box = await sidebarSessions.boundingBox();
  expect(box).not.toBeNull();
  expect(box!.x).toBeGreaterThanOrEqual(0);
});
