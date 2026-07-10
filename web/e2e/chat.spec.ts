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

test.beforeEach(async ({ page }) => {
  await page.route(`${ROUTER_ORIGIN}/v1/sessions?**`, async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: "[]" });
  });

  await page.route(`${ROUTER_ORIGIN}/v1/sessions`, async (route) => {
    if (route.request().method() !== "POST") return route.continue();
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ id: "test-session-id", project: "default" }),
    });
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

  await expect(page.getByTestId("counter-display-status")).toHaveText("Ready when you are");

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
  await expect(page.getByTestId("counter-display-status")).toHaveText("Order up");
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
