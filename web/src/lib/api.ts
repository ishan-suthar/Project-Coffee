import { streamSSE } from "@/lib/sse";
import { authFetch, clearStoredUser, setStoredUser, setToken } from "@/lib/authFetch";
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

export interface LoginResult {
  token: string;
  user: { id: number; username: string; display_name: string };
}

/** POST /v1/login (Brew 43) - the only unauthenticated router call in
 * this file. Stores the returned token via setToken() so every
 * subsequent authFetch()/streamSSE() call picks it up automatically. */
export async function login(username: string, password: string): Promise<LoginResult> {
  const response = await fetch(`${ROUTER_BASE_URL}/v1/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  if (!response.ok) {
    throw new Error("Invalid username or password.");
  }
  const result: LoginResult = await response.json();
  setToken(result.token);
  setStoredUser(result.user);
  return result;
}

export async function logout(): Promise<void> {
  await authFetch(`${ROUTER_BASE_URL}/v1/logout`, { method: "POST" }).catch(() => {
    // Best-effort - even if the router call fails (e.g. already expired),
    // the caller still clears the local token and redirects.
  });
  clearStoredUser();
}

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

  const response = await authFetch(`${ROUTER_BASE_URL}/v1/upload`, {
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
  const response = await authFetch(`${ROUTER_BASE_URL}/v1/sessions/${sessionId}/pending_escalation`);
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

/** project_id: undefined/null creates the session under "default" (no
 * project) - Brew 43, docs/design/auth-projects-chat-management-design.md
 * Section 4.1. */
export async function createSession(
  projectId?: number | null
): Promise<{ id: string; project_id: number | null }> {
  return postJSON("/v1/sessions", { project_id: projectId ?? null });
}

/** projectId: omit for "default" (project_id IS NULL), a real project id
 * for that project, or the literal string "all" for "All chats". */
export async function listSessions(
  projectId?: number | "all" | null
): Promise<SessionSummary[]> {
  const params: Record<string, string> = {};
  if (projectId !== undefined && projectId !== null) params.project_id = String(projectId);
  const response = await authFetch(
    `${ROUTER_BASE_URL}/v1/sessions?${new URLSearchParams(params).toString()}`
  );
  if (!response.ok) throw new Error(`Failed to list sessions: ${response.status}`);
  return response.json();
}

export async function getSessionMessages(sessionId: string): Promise<StoredMessage[]> {
  const response = await authFetch(`${ROUTER_BASE_URL}/v1/sessions/${sessionId}/messages`);
  if (!response.ok) throw new Error(`Failed to load session messages: ${response.status}`);
  return response.json();
}

/** PATCH /v1/sessions/{id} (Brew 43) - always overwrites the title,
 * unlike the router's own first-message auto-title. */
export async function renameSession(
  sessionId: string,
  title: string
): Promise<{ id: string; title: string }> {
  return patchJSON(`/v1/sessions/${sessionId}`, { title });
}

/** DELETE /v1/sessions/{id} (Brew 43) - soft delete server-side; the
 * session disappears from every list/read path immediately. */
export async function deleteSession(sessionId: string): Promise<void> {
  await deleteRequest(`/v1/sessions/${sessionId}`);
}

/** PATCH /v1/sessions/{id} (Brew 46) - flips the session's remember_chat
 * toggle. Never deletes anything; OFF just stops history assembly on the
 * *next* request, ON resumes with whatever is already stored. See
 * docs/design/conversation-memory-design.md Section 1. */
export async function setRememberChat(
  sessionId: string,
  rememberChat: boolean
): Promise<{ id: string; remember_chat: boolean }> {
  return patchJSON(`/v1/sessions/${sessionId}`, { remember_chat: rememberChat });
}

export interface ProjectSummary {
  id: number;
  name: string;
  created_at: string;
  updated_at: string;
}

export async function createProject(name: string): Promise<ProjectSummary> {
  return postJSON("/v1/projects", { name });
}

export async function listProjects(): Promise<ProjectSummary[]> {
  const response = await authFetch(`${ROUTER_BASE_URL}/v1/projects`);
  if (!response.ok) throw new Error(`Failed to list projects: ${response.status}`);
  return response.json();
}

export async function renameProject(
  projectId: number,
  name: string
): Promise<{ id: number; name: string }> {
  return patchJSON(`/v1/projects/${projectId}`, { name });
}

/** Deletes the project - the router moves its sessions to "default"
 * rather than deleting them. */
export async function deleteProject(projectId: number): Promise<void> {
  await deleteRequest(`/v1/projects/${projectId}`);
}

export async function listBeans(): Promise<Bean[]> {
  const response = await authFetch(`${ROUTER_BASE_URL}/v1/beans`);
  if (!response.ok) throw new Error(`Failed to list beans: ${response.status}`);
  return response.json();
}

/** GET /v1/pantry/file (Brew 41) - read-only file viewer content for a
 * citation chip. path must be one of the sources the router itself
 * reported in a `complete` event's pantry_sources - the router 404s on
 * anything outside knowledge/ regardless. */
export async function getPantryFile(path: string): Promise<PantryFileContent> {
  const response = await authFetch(
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

export interface PolicyRebuildPreviewResult {
  proposal_id: string;
  diff: string;
  escalation_candidates: string[];
}

/** POST /v1/policy/rebuild_preview (Brew 42) - computes a proposed
 * router/config/routing_policy.yaml rebuild (Roastery Cup Test evidence
 * blended with real accumulated ratings) and returns a diff. Never
 * writes anything - only rebuildPolicyApply() does that. */
export async function rebuildPolicyPreview(): Promise<PolicyRebuildPreviewResult> {
  return postJSON("/v1/policy/rebuild_preview", {});
}

export async function rebuildPolicyApply(
  proposalId: string
): Promise<{ proposal_id: string; status: string }> {
  return postJSON(`/v1/policy/rebuild_apply/${proposalId}`, {});
}

export async function rebuildPolicyDiscard(
  proposalId: string
): Promise<{ proposal_id: string; status: string }> {
  return postJSON(`/v1/policy/rebuild_discard/${proposalId}`, {});
}

async function postJSON<T = unknown>(path: string, body: unknown): Promise<T> {
  const response = await authFetch(`${ROUTER_BASE_URL}${path}`, {
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

async function patchJSON<T = unknown>(path: string, body: unknown): Promise<T> {
  const response = await authFetch(`${ROUTER_BASE_URL}${path}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    const detail = await response.text().catch(() => "");
    throw new Error(`PATCH ${path} failed with ${response.status}: ${detail}`);
  }
  return response.json();
}

async function deleteRequest(path: string): Promise<void> {
  const response = await authFetch(`${ROUTER_BASE_URL}${path}`, { method: "DELETE" });
  if (!response.ok) {
    const detail = await response.text().catch(() => "");
    throw new Error(`DELETE ${path} failed with ${response.status}: ${detail}`);
  }
}
