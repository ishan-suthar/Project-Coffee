import { NextRequest, NextResponse } from "next/server";

/**
 * Brew 43 (docs/design/auth-projects-chat-management-design.md Section
 * 6.2): redirects to /login when the token cookie is absent. This is a
 * UX convenience, not the real security boundary - it only checks
 * cookie *presence*, never validity (that would need a network round
 * trip to the router on every navigation). The router's
 * get_current_user dependency validating the real token on every
 * request is what actually enforces auth; a forged or stale cookie
 * passes this check and then gets a real 401 from the router, which
 * authFetch() turns into the same /login redirect.
 *
 * Named `proxy.ts`, not `middleware.ts` - this Next.js version (16)
 * deprecated the `middleware` file convention in favor of `proxy`
 * (see node_modules/next/dist/docs/.../file-conventions/proxy.md),
 * confirmed directly rather than assumed after a build-time deprecation
 * warning surfaced it.
 */
const TOKEN_COOKIE_NAME = "coffee_counter_token";

export function proxy(request: NextRequest) {
  const hasToken = request.cookies.has(TOKEN_COOKIE_NAME);
  const isLoginPage = request.nextUrl.pathname.startsWith("/login");

  if (!hasToken && !isLoginPage) {
    return NextResponse.redirect(new URL("/login", request.url));
  }
  if (hasToken && isLoginPage) {
    return NextResponse.redirect(new URL("/", request.url));
  }
  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico|assets).*)"],
};
