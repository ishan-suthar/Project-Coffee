import { afterEach, describe, expect, it, vi } from "vitest";

// ROUTER_BASE_URL is a module-level const read from process.env at import
// time (LAN access support - see router/README.md and web/README.md's
// "LAN access" sections). vi.resetModules() + a fresh dynamic import per
// test is required to observe a different env value, since Vitest (like
// Next.js) otherwise caches the module after first import.

describe("ROUTER_BASE_URL", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.resetModules();
  });

  it("defaults to http://127.0.0.1:8765 when NEXT_PUBLIC_ROUTER_URL is unset", async () => {
    vi.stubEnv("NEXT_PUBLIC_ROUTER_URL", undefined);
    vi.resetModules();
    const { ROUTER_BASE_URL } = await import("@/lib/api");
    expect(ROUTER_BASE_URL).toBe("http://127.0.0.1:8765");
  });

  it("uses NEXT_PUBLIC_ROUTER_URL when set, e.g. a LAN IP", async () => {
    vi.stubEnv("NEXT_PUBLIC_ROUTER_URL", "http://192.168.1.42:8765");
    vi.resetModules();
    const { ROUTER_BASE_URL } = await import("@/lib/api");
    expect(ROUTER_BASE_URL).toBe("http://192.168.1.42:8765");
  });
});
