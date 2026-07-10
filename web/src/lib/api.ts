import { streamSSE } from "@/lib/sse";
import type { Bean, Rating, RouterEvent, SessionSummary, StoredMessage } from "@/lib/events";
import type { UploadResponse } from "@/lib/attachments";

export const ROUTER_BASE_URL =
  process.env.NEXT_PUBLIC_ROUTER_URL ?? "http://127.0.0.1:8765";

interface OrderOptions {
  sessionId?: string;
  beanAliasOverride?: string;
  attachmentIds?: string[];
  requestId?: string;
  signal?: AbortSignal;
}

export function orderStream(prompt: string, options: OrderOptions = {}): AsyncGenerator<RouterEvent> {
  return streamSSE(
    `${ROUTER_BASE_URL}/v1/order`,
    {
      prompt,
      session_id: options.sessionId ?? null,
      bean_alias_override: options.beanAliasOverride ?? null,
      attachment_ids: options.attachmentIds ?? [],
      request_id: options.requestId ?? null,
    },
    options.signal
  );
}

export async function uploadFile(
  requestId: string,
  file: File,
  signal?: AbortSignal
): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append("request_id", requestId);
  formData.append("file", file);

  const response = await fetch(`${ROUTER_BASE_URL}/v1/upload`, {
    method: "POST",
    body: formData,
    signal,
  });

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail ?? `Upload failed with ${response.status}`);
  }
  return response.json();
}

export function retryStream(requestId: string, signal?: AbortSignal): AsyncGenerator<RouterEvent> {
  return streamSSE(`${ROUTER_BASE_URL}/v1/retry`, { request_id: requestId }, signal);
}

export async function approveEscalation(requestId: string, approve: boolean): Promise<void> {
  await postJSON("/v1/approve_escalation", { request_id: requestId, approve });
}

export async function cancelOrder(requestId: string): Promise<void> {
  await postJSON("/v1/cancel", { request_id: requestId });
}

export async function rateMessage(requestId: string, rating: Rating): Promise<void> {
  await postJSON("/v1/rate", { request_id: requestId, rating });
}

export async function createSession(project: string): Promise<{ id: string; project: string }> {
  return postJSON("/v1/sessions", { project });
}

export async function listSessions(project: string): Promise<SessionSummary[]> {
  const response = await fetch(
    `${ROUTER_BASE_URL}/v1/sessions?${new URLSearchParams({ project }).toString()}`
  );
  if (!response.ok) throw new Error(`Failed to list sessions: ${response.status}`);
  return response.json();
}

export async function getSessionMessages(sessionId: string): Promise<StoredMessage[]> {
  const response = await fetch(`${ROUTER_BASE_URL}/v1/sessions/${sessionId}/messages`);
  if (!response.ok) throw new Error(`Failed to load session messages: ${response.status}`);
  return response.json();
}

export async function listBeans(): Promise<Bean[]> {
  const response = await fetch(`${ROUTER_BASE_URL}/v1/beans`);
  if (!response.ok) throw new Error(`Failed to list beans: ${response.status}`);
  return response.json();
}

async function postJSON<T = unknown>(path: string, body: unknown): Promise<T> {
  const response = await fetch(`${ROUTER_BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    const detail = await response.text().catch(() => "");
    throw new Error(`POST ${path} failed with ${response.status}: ${detail}`);
  }
  return response.json();
}
