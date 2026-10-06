import { ROUTER_BASE_URL } from "@/lib/api";

/**
 * Device-wide UI preferences (docs/design/counter-scene-design.md
 * Section 5) - backed by router/app/preferences.py, not localStorage
 * (unavailable in some environments the router UI runs in).
 */
export async function getPreferences(): Promise<Record<string, string>> {
  const response = await fetch(`${ROUTER_BASE_URL}/v1/preferences`);
  if (!response.ok) throw new Error(`Failed to load preferences: ${response.status}`);
  return response.json();
}

export async function setPreference(key: string, value: string): Promise<void> {
  const response = await fetch(`${ROUTER_BASE_URL}/v1/preferences`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ key, value }),
  });
  if (!response.ok) throw new Error(`Failed to save preference: ${response.status}`);
}
