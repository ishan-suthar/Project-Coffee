import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  authFetch,
  authHeader,
  clearStoredUser,
  clearToken,
  getStoredUser,
  getToken,
  setStoredUser,
  setToken,
} from "@/lib/authFetch";

function clearAllCookies() {
  document.cookie.split(";").forEach((c) => {
    const name = c.split("=")[0].trim();
    if (name) document.cookie = `${name}=; path=/; max-age=0`;
  });
}

describe("authFetch token storage", () => {
  beforeEach(() => {
    clearAllCookies();
    window.localStorage.clear();
  });

  afterEach(() => {
    clearAllCookies();
    window.localStorage.clear();
  });

  it("getToken returns null when no token cookie is set", () => {
    expect(getToken()).toBeNull();
  });

  it("setToken then getToken round-trips", () => {
    setToken("abc123");
    expect(getToken()).toBe("abc123");
  });

  it("clearToken removes the token", () => {
    setToken("abc123");
    clearToken();
    expect(getToken()).toBeNull();
  });

  it("authHeader is empty when no token is set", () => {
    expect(authHeader()).toEqual({});
  });

  it("authHeader carries the Bearer token when set", () => {
    setToken("abc123");
    expect(authHeader()).toEqual({ Authorization: "Bearer abc123" });
  });

  it("getStoredUser returns null when nothing is stored", () => {
    expect(getStoredUser()).toBeNull();
  });

  it("setStoredUser then getStoredUser round-trips", () => {
    setStoredUser({ id: 1, username: "alice", display_name: "Alice" });
    expect(getStoredUser()).toEqual({ id: 1, username: "alice", display_name: "Alice" });
  });

  it("clearStoredUser removes the stored user", () => {
    setStoredUser({ id: 1, username: "alice", display_name: "Alice" });
    clearStoredUser();
    expect(getStoredUser()).toBeNull();
  });
});

describe("authFetch()", () => {
  beforeEach(() => {
    clearAllCookies();
    window.localStorage.clear();
    vi.stubGlobal("fetch", vi.fn());
    delete (window as unknown as { location?: unknown }).location;
    (window as unknown as { location: { href: string } }).location = { href: "" };
  });

  afterEach(() => {
    clearAllCookies();
    window.localStorage.clear();
    vi.unstubAllGlobals();
  });

  it("attaches the Authorization header when a token is set", async () => {
    setToken("abc123");
    vi.mocked(fetch).mockResolvedValue(new Response("{}", { status: 200 }));

    await authFetch("http://router/v1/beans");

    const [, init] = vi.mocked(fetch).mock.calls[0];
    const headers = new Headers(init?.headers);
    expect(headers.get("Authorization")).toBe("Bearer abc123");
  });

  it("does not attach an Authorization header when no token is set", async () => {
    vi.mocked(fetch).mockResolvedValue(new Response("{}", { status: 200 }));

    await authFetch("http://router/v1/beans");

    const [, init] = vi.mocked(fetch).mock.calls[0];
    const headers = new Headers(init?.headers);
    expect(headers.has("Authorization")).toBe(false);
  });

  it("clears the token and redirects to /login on a 401 response", async () => {
    setToken("abc123");
    vi.mocked(fetch).mockResolvedValue(new Response("{}", { status: 401 }));

    await authFetch("http://router/v1/beans");

    expect(getToken()).toBeNull();
    expect(window.location.href).toBe("/login");
  });

  it("does not redirect on a non-401 response", async () => {
    setToken("abc123");
    vi.mocked(fetch).mockResolvedValue(new Response("{}", { status: 200 }));

    await authFetch("http://router/v1/beans");

    expect(getToken()).toBe("abc123");
    expect(window.location.href).toBe("");
  });
});
