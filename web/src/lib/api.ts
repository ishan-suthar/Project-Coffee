import { streamSSE } from "@/lib/sse";
import type {
  Bean,
  PendingEscalationInfo,
  Rating,
  RouterEvent,
  SessionSummary,
  StoredMessage,
} from "@/lib/events";
import type { UploadResponse } from "@/lib/attachments";

export const ROUTER_BASE_URL =
  process.env.NEXT_PUBLIC_ROUTER_URL ?? "http://127.0.0.1:8765";

interface OrderOptions {
  sessionId?: string;
  beanAliasOverride?: string;
  attachmentIds?: string[];
  requestId?: string;
  usePantry?: boolean;
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
      use_pantry: options.usePantry ?? false,
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

export interface ApproveEscalationResult {
  request_id: string;
  status: "acknowledged" | "already_resolved";
  approve?: boolean;
  resolution?: "approved" | "declined" | "timed_out" | "cancelled";
}

export async function approveEscalation(
  requestId: string,
  approve: boolean
): Promise<ApproveEscalationResult> {
  return postJSON("/v1/approve_escalation", { request_id: requestId, approve });
}

/** GET /v1/sessions/{id}/pending_escalation (Brew 40) - null when no
 * escalation is currently awaiting a decision for that session (the
 * normal case), not an error. See docs/design/
 * escalation-approval-ui-design.md Section 3.5. */
export async function getPendingEscalation(sessionId: string): Promise<PendingEscalationInfo | null> {
  const response = await fetch(`${ROUTER_BASE_URL}/v1/sessions/${sessionId}/pending_escalation`);
  if (response.status === 404) return null;
  if (!response.ok) throw new Error(`Failed to load pending escalation: ${response.status}`);
  return response.json();
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

/** GET /v1/pantry/file (Brew 41) - read-only file viewer content for a
 * citation chip. path must be one of the sources the router itself
 * reported in a `complete` event's pantry_sources - the router 404s on
 * anything outside knowledge/ regardless. */
export async function getPantryFile(path: string): Promise<PantryFileContent> {
  const response = await fetch(
    `${ROUTER_BASE_URL}/v1/pantry/file?${new URLSearchParams({ path }).toString()}`
  );
  if (!response.ok) throw new Error(`Failed to load Pantry file: ${response.status}`);
  return response.json();
}

export interface PantryFileContent {
  path: string;
  content: string;
}

export interface MemoryProposalFile {
  path: string;
  diff: string;
  new_content: string;
}

export interface MemoryProposalResult {
  proposal_id: string;
  files: MemoryProposalFile[];
}

/** POST /v1/sessions/{id}/memory_proposal (Brew 41) - generates a
 * reviewable proposal, never writes anything. Throws on a 422 guardrail
 * or parse failure - the caller shows the error, there is no partial
 * proposal to render. */
export async function generateMemoryProposal(sessionId: string): Promise<MemoryProposalResult> {
  return postJSON(`/v1/sessions/${sessionId}/memory_proposal`, {});
}

export async function approveMemoryProposal(
  proposalId: string
): Promise<{ proposal_id: string; status: string }> {
  return postJSON(`/v1/memory_proposals/${proposalId}/approve`, {});
}

export async function discardMemoryProposal(
  proposalId: string
): Promise<{ proposal_id: string; status: string }> {
  return postJSON(`/v1/memory_proposals/${proposalId}/discard`, {});
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
