"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import * as api from "@/lib/api";

/** Brew 43 (docs/design/auth-projects-chat-management-design.md Section
 * 6.2): the only way in - there is no signup form, users are added via
 * router/tools/manage_users.py only. */
export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setErrorMessage(null);
    setSubmitting(true);
    try {
      await api.login(username, password);
      router.push("/");
    } catch {
      setErrorMessage("Invalid username or password.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-cream px-4">
      <div className="w-full max-w-sm rounded-lg border border-caramel bg-latte p-6 shadow-sm">
        <div className="mb-4 flex flex-col items-center gap-2">
          {/* eslint-disable-next-line @next/next/no-img-element -- static branding SVG, not user content */}
          <img src="/assets/branding/coffee_logo.svg" alt="" className="h-12 w-12" />
          <h1 className="text-lg font-medium text-espresso">Sign in to Coffee Counter</h1>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col gap-3">
          <label className="flex flex-col gap-1 text-sm text-espresso">
            Username
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoFocus
              required
              className="rounded border border-caramel bg-cream px-3 py-2 text-sm text-espresso outline-none focus:border-crema-amber"
            />
          </label>

          <label className="flex flex-col gap-1 text-sm text-espresso">
            Password
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="rounded border border-caramel bg-cream px-3 py-2 text-sm text-espresso outline-none focus:border-crema-amber"
            />
          </label>

          {errorMessage && (
            <p className="text-sm text-crema-amber" data-testid="login-error">
              {errorMessage}
            </p>
          )}

          <button
            type="submit"
            disabled={submitting || username.trim().length === 0 || password.length === 0}
            className="mt-2 rounded bg-crema-amber px-4 py-2 text-sm text-cream transition hover:opacity-90 disabled:opacity-50"
          >
            {submitting ? "Signing in…" : "Sign in"}
          </button>
        </form>
      </div>
    </div>
  );
}
