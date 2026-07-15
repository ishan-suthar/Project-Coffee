import type { RouterEvent } from "@/lib/events";
import { authHeader, redirectToLogin } from "@/lib/authFetch";

/**
 * Streams Server-Sent Events from a POST endpoint using fetch() + a
 * ReadableStream reader, not the native EventSource API.
 *
 * Native EventSource only supports GET with no request body, but
 * POST /v1/order and POST /v1/retry need a JSON body (the prompt).
 * Sending the prompt as a GET query string instead would put chat
 * content in URLs, server logs, and browser history - see
 * docs/design/coffee-counter-chat-ui-design.md Section 2.1. This is the
 * standard workaround for that EventSource limitation: same
 * `data: <json>\n\n` SSE protocol, just parsed manually.
 */
export async function* streamSSE(
  url: string,
  body: unknown,
  signal?: AbortSignal
): AsyncGenerator<RouterEvent> {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeader() },
    body: JSON.stringify(body),
    signal,
  });

  if (response.status === 401) {
    redirectToLogin();
  }
  if (!response.ok) {
    const detail = await response.text().catch(() => "");
    throw new Error(`Request to ${url} failed with ${response.status}: ${detail}`);
  }
  if (!response.body) {
    throw new Error(`Request to ${url} returned no readable body.`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      let frameEnd = buffer.indexOf("\n\n");
      while (frameEnd !== -1) {
        const frame = buffer.slice(0, frameEnd);
        buffer = buffer.slice(frameEnd + 2);
        yield* parseSSEFrame(frame);
        frameEnd = buffer.indexOf("\n\n");
      }
    }

    // Flush any trailing frame that arrived without a final \n\n
    // (can happen if the server closes the connection right after the
    // last event without a trailing blank line).
    if (buffer.trim().length > 0) {
      yield* parseSSEFrame(buffer);
    }
  } finally {
    reader.releaseLock();
  }
}

function* parseSSEFrame(frame: string): Generator<RouterEvent> {
  for (const line of frame.split("\n")) {
    if (!line.startsWith("data:")) continue;
    const payload = line.slice("data:".length).trim();
    if (!payload) continue;
    try {
      yield JSON.parse(payload) as RouterEvent;
    } catch {
      // Malformed frame - skip rather than crash the whole stream.
      // A real backend bug here should surface as a missing `complete`
      // event, which the UI already treats as a stalled/failed request.
      continue;
    }
  }
}
