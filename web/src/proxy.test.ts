import { describe, expect, it } from "vitest";
import { NextRequest } from "next/server";
import { proxy } from "@/proxy";

function makeRequest(path: string, cookies: Record<string, string> = {}): NextRequest {
  const request = new NextRequest(new URL(path, "http://localhost:3000"));
  for (const [name, value] of Object.entries(cookies)) {
    request.cookies.set(name, value);
  }
  return request;
}

describe("proxy", () => {
  it("redirects to /login when no token cookie is present", () => {
    const response = proxy(makeRequest("/"));
    expect(response.status).toBe(307);
    expect(response.headers.get("location")).toBe("http://localhost:3000/login");
  });

  it("passes through to / when a token cookie is present", () => {
    const response = proxy(makeRequest("/", { coffee_counter_token: "abc123" }));
    expect(response.status).toBe(200);
  });

  it("does not redirect /login itself when no token is present", () => {
    const response = proxy(makeRequest("/login"));
    expect(response.status).toBe(200);
  });

  it("redirects away from /login when already authenticated", () => {
    const response = proxy(makeRequest("/login", { coffee_counter_token: "abc123" }));
    expect(response.status).toBe(307);
    expect(response.headers.get("location")).toBe("http://localhost:3000/");
  });
});
