/**
 * Brew 43 (docs/design/auth-projects-chat-management-design.md Section
 * 6.1, Gap 1): the router (127.0.0.1:8765) and this frontend
 * (localhost:3000) are different origins over plain local HTTP - a real
 * HttpOnly cross-origin cookie would need SameSite=None; Secure, and
 * Secure cookies require HTTPS, which this stack doesn't have. So the
 * token lives in a plain (non-HttpOnly), JS-readable cookie, and every
 * request attaches it explicitly as `Authorization: Bearer <token>`
 * rather than relying on the browser to send it automatically. This is
 * a deliberate, disclosed trade-off, not an accidental downgrade.
 */

const TOKEN_COOKIE_NAME = "coffee_counter_token";

export function getToken(): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(new RegExp(`(?:^|; )${TOKEN_COOKIE_NAME}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
}

export function setToken(token: string): void {
  // 30 days, matching the router's token TTL - a stale cookie outliving
  // its token would just mean a future 401, not a security issue.
  const maxAgeSeconds = 30 * 24 * 60 * 60;
  document.cookie = `${TOKEN_COOKIE_NAME}=${encodeURIComponent(token)}; path=/; max-age=${maxAgeSeconds}; SameSite=Lax`;
}

export function clearToken(): void {
  document.cookie = `${TOKEN_COOKIE_NAME}=; path=/; max-age=0`;
}

/** Redirects to /login - called both on an explicit sign-out and
 * reactively whenever any request comes back 401 (expired/invalid
 * token, or no token at all). Uses window.location rather than Next's
 * router since this is called from plain lib code (chatStore actions),
 * not React component context. */
function redirectToLogin(): void {
  clearToken();
  if (typeof window !== "undefined") {
    window.location.href = "/login";
  }
}

/** Wraps fetch() to attach the Authorization header and react to a 401
 * by clearing the token and redirecting to /login. Every router call in
 * api.ts and sse.ts goes through this (or attaches the header the same
 * way) rather than a bare fetch(). */
export async function authFetch(input: string, init: RequestInit = {}): Promise<Response> {
  const token = getToken();
  const headers = new Headers(init.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const response = await fetch(input, { ...init, headers });
  if (response.status === 401) {
    redirectToLogin();
  }
  return response;
}

/** For streamSSE() (web/src/lib/sse.ts), which needs the raw header
 * value rather than a wrapped fetch() - it does its own ReadableStream
 * handling and can't share authFetch()'s Response-based 401 check
 * cleanly. */
export function authHeader(): Record<string, string> {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

const USER_STORAGE_KEY = "coffee_counter_user";

export interface StoredUser {
  id: number;
  username: string;
  display_name: string;
}

/** localStorage, not the token cookie - this is display-only data (never
 * used for authorization, the router re-validates the real token on
 * every request), so it doesn't need the same cross-origin handling.
 * Lets Sidebar show the display name / Sign out button again after a
 * full page reload without a "who am I" endpoint to call. */
export function setStoredUser(user: StoredUser): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(user));
}

export function getStoredUser(): StoredUser | null {
  if (typeof window === "undefined") return null;
  const raw = window.localStorage.getItem(USER_STORAGE_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as StoredUser;
  } catch {
    return null;
  }
}

export function clearStoredUser(): void {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(USER_STORAGE_KEY);
}

export { redirectToLogin };
