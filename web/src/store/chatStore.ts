import { create } from "zustand";
import { v4 as uuidv4 } from "@/lib/uuid";
import * as api from "@/lib/api";
import type { ProjectSummary } from "@/lib/api";
import type { Rating, SessionSummary } from "@/lib/events";
import {
  AttachmentSummary,
  ChatMessage,
  newAssistantMessage,
  newUserMessage,
  reduceEventIntoMessage,
} from "@/lib/chat";

// Brew 40: how often/how long a recovered (no-live-stream) escalation
// card polls GET /v1/sessions/{id}/messages for the eventual result once
// a decision is sent - see docs/design/escalation-approval-ui-design.md
// Section 3.5's explicit "polling, not live reattachment" scope call.
const RECOVERED_ESCALATION_POLL_INTERVAL_MS = 2000;
const RECOVERED_ESCALATION_POLL_MAX_ATTEMPTS = 30;

// Brew 43 (docs/design/auth-projects-chat-management-design.md Section
// 4.2, Question 3): an explicit discriminated selection rather than a
// bare string, so "All chats" and a real project a user happened to name
// "default" can never collide with the sentinel.
export type ProjectFilter = "all" | "default" | ProjectSummary;

interface SendPromptOptions {
  beanAliasOverride?: string;
  // Brew 38: attachmentIds are resolved server-side against state.uploads;
  // attachments is the UI-only summary (filename/size/thumbnail) rendered
  // immediately for the sent user message; requestId is the client-
  // generated id the attachments were uploaded under (see
  // docs/design/attachments-design.md Section 7, Decision 2) - undefined
  // for a plain text message, which lets the server generate one as before.
  attachmentIds?: string[];
  attachments?: AttachmentSummary[];
  requestId?: string;
  // Brew 41: per-request Pantry retrieval toggle (OrderBox's "Use
  // Pantry" checkbox) - not a session-wide setting.
  usePantry?: boolean;
}

interface ChatState {
  projectFilter: ProjectFilter;
  projects: ProjectSummary[];
  activeSessionId: string | null;
  sessions: SessionSummary[];
  sessionsLoaded: boolean;
  messages: Record<string, ChatMessage[]>; // keyed by sessionId; "" holds messages for a not-yet-created session
  activeRequestId: string | null;
  abortController: AbortController | null;

  loadSessions: () => Promise<void>;
  selectSession: (sessionId: string) => Promise<void>;
  startNewSession: () => void;
  sendPrompt: (prompt: string, options?: SendPromptOptions) => Promise<void>;
  cancelActive: () => Promise<void>;
  rate: (requestId: string, rating: Rating) => Promise<void>;
  rebrew: (message: ChatMessage, beanAliasOverride?: string) => Promise<void>;
  // Brew 40 (docs/design/escalation-approval-ui-design.md): sends a
  // decision for a pending escalation - works for both the live path
  // (the open SSE stream picks up the resulting escalating/complete
  // events itself) and a reload-recovered card (which has no live
  // stream, so this also starts polling for the eventual result).
  approveEscalation: (requestId: string, approve: boolean) => Promise<void>;
  // Checks GET /v1/sessions/{id}/pending_escalation and, if one is open,
  // appends a synthetic in-progress assistant message so the approval
  // card renders even though this client never saw the live
  // escalation_pending event. No-ops if nothing is pending.
  recoverPendingEscalation: (sessionId: string) => Promise<void>;

  // Brew 43 (docs/design/auth-projects-chat-management-design.md
  // Section 4): project CRUD + selecting which project's sessions are
  // shown. Chat management (rename/delete a session) lives here too.
  setProjectFilter: (filter: ProjectFilter) => void;
  loadProjects: () => Promise<void>;
  createProject: (name: string) => Promise<void>;
  renameProject: (projectId: number, name: string) => Promise<void>;
  deleteProject: (projectId: number) => Promise<void>;
  renameSession: (sessionId: string, title: string) => Promise<void>;
  deleteSession: (sessionId: string) => Promise<void>;

  // Brew 46 (docs/design/conversation-memory-design.md Section 1):
  // optimistic - flips the local sessions array immediately, then
  // reverts on a failed PATCH so the UI never shows a state the router
  // didn't actually persist.
  setRememberChat: (sessionId: string, rememberChat: boolean) => Promise<void>;
}

export const useChatStore = create<ChatState>((set, get) => ({
  projectFilter: "default",
  projects: [],
  activeSessionId: null,
  sessions: [],
  sessionsLoaded: false,
  messages: {},
  activeRequestId: null,
  abortController: null,

  loadSessions: async () => {
    const filter = get().projectFilter;
    const projectId = filter === "all" ? "all" : filter === "default" ? undefined : filter.id;
    const sessions = await api.listSessions(projectId);
    set({ sessions, sessionsLoaded: true });
  },

  selectSession: async (sessionId: string) => {
    set({ activeSessionId: sessionId });
    if (get().messages[sessionId]) return;
    const stored = await api.getSessionMessages(sessionId);
    const messages: ChatMessage[] = stored.map((m) => ({
      id: m.role === "assistant" ? m.request_id : m.id,
      role: m.role,
      content: m.content,
      requestId: m.request_id,
      isStreaming: false,
      latestEvent: null,
      beanAlias: m.bean_alias,
      taskType: m.task_type,
      complexity: m.complexity,
      costUsd: m.cost_usd,
      latencyMs: m.latency_ms,
      escalated: m.escalated ?? false,
      draftQuality: m.draft_quality ?? false,
      escalation: null,
      rating: m.rating,
      errorMessage: null,
      // Session history re-displays no attachment content (the router
      // only reports has_attachments, a cheap boolean, not the extracted
      // text/original file - see docs/design/conversation-memory-design.md
      // Section 3) - attachments stays [] for a loaded-from-history
      // message, hasAttachments carries the boolean the toggle hint needs.
      attachments: [],
      pendingEscalationRecovered: false,
      // Session history has no Pantry-source persistence either (same
      // reasoning as attachments above - SessionStore doesn't store it).
      pantrySources: null,
      historyTurnsIncluded: null,
      historyTokensEst: null,
      hasAttachments: m.has_attachments,
    }));
    set((state) => ({ messages: { ...state.messages, [sessionId]: messages } }));

    await get().recoverPendingEscalation(sessionId);
  },

  startNewSession: () => {
    set({ activeSessionId: null });
  },

  sendPrompt: async (prompt: string, options: SendPromptOptions = {}) => {
    let sessionId = get().activeSessionId;
    if (sessionId === null) {
      const filter = get().projectFilter;
      const projectId = filter === "all" || filter === "default" ? null : filter.id;
      const created = await api.createSession(projectId);
      sessionId = created.id;
      set({ activeSessionId: sessionId });
      await get().loadSessions();
    }

    const key = sessionId;
    const userMessage = newUserMessage(uuidv4(), prompt, options.attachments ?? []);
    appendMessage(set, key, userMessage);

    const controller = new AbortController();
    set({ abortController: controller });

    let assistantMessage: ChatMessage | null = null;

    try {
      for await (const event of api.orderStream(prompt, {
        sessionId: key,
        beanAliasOverride: options.beanAliasOverride,
        attachmentIds: options.attachmentIds,
        requestId: options.requestId,
        usePantry: options.usePantry,
        signal: controller.signal,
      })) {
        if (assistantMessage === null) {
          assistantMessage = newAssistantMessage(event.request_id);
          appendMessage(set, key, assistantMessage);
          set({ activeRequestId: event.request_id });
        }
        assistantMessage = reduceEventIntoMessage(assistantMessage, event);
        updateMessage(set, key, assistantMessage);
      }
    } catch (err) {
      if (assistantMessage !== null) {
        updateMessage(set, key, { ...assistantMessage, isStreaming: false });
      }
      if (!(err instanceof DOMException && err.name === "AbortError")) {
        throw err;
      }
    } finally {
      set({ activeRequestId: null, abortController: null });
      await get().loadSessions(); // refresh sidebar cost totals / ordering
    }
  },

  cancelActive: async () => {
    const { activeRequestId, abortController } = get();
    if (activeRequestId !== null) {
      await api.cancelOrder(activeRequestId).catch(() => {
        // Best-effort: if the router has already finished the request,
        // /v1/cancel 404s - the abort() below still stops local rendering.
      });
    }
    abortController?.abort();
  },

  rate: async (requestId: string, rating: Rating) => {
    await api.rateMessage(requestId, rating);
    const sessionId = get().activeSessionId;
    if (sessionId === null) return;
    set((state) => ({
      messages: {
        ...state.messages,
        [sessionId]: (state.messages[sessionId] ?? []).map((m) =>
          m.requestId === requestId ? { ...m, rating } : m
        ),
      },
    }));
  },

  rebrew: async (message: ChatMessage, beanAliasOverride?: string) => {
    const sessionId = get().activeSessionId;
    if (sessionId === null) return;
    const priorUserMessage = findPriorUserMessage(get().messages[sessionId] ?? [], message.id);
    if (priorUserMessage === null) return;
    // Attachments are not resent on a re-brew (out of scope - the original
    // File objects are gone by the time a re-brew happens).
    await get().sendPrompt(priorUserMessage.content, { beanAliasOverride });
  },

  approveEscalation: async (requestId: string, approve: boolean) => {
    await api.approveEscalation(requestId, approve);

    const sessionId = get().activeSessionId;
    if (sessionId === null) return;

    const message = (get().messages[sessionId] ?? []).find((m) => m.requestId === requestId);
    if (message?.pendingEscalationRecovered) {
      await pollForRecoveredResult(set, get, sessionId, requestId);
    }
    // Live path: nothing else to do here - the already-open SSE stream
    // (started by the original sendPrompt call) receives the resulting
    // escalating/complete/cancelled event on its own and updates the
    // message through the normal reduceEventIntoMessage path.
  },

  recoverPendingEscalation: async (sessionId: string) => {
    const pending = await api.getPendingEscalation(sessionId).catch(() => null);
    if (pending === null) return;
    // Don't clobber a card already being tracked (e.g. recoverPendingEscalation
    // called twice for the same session).
    if ((get().messages[sessionId] ?? []).some((m) => m.requestId === pending.request_id)) return;

    const message: ChatMessage = {
      ...newAssistantMessage(pending.request_id),
      escalation: {
        reason: pending.reason,
        estCostUsd: pending.est_cost_usd,
        premiumBeanAlias: pending.premium_bean_alias,
        decisionDeadline: pending.decision_deadline,
      },
      latestEvent: {
        event: "escalation_pending",
        request_id: pending.request_id,
        ts: pending.started_at,
        reason: pending.reason,
        est_cost_usd: pending.est_cost_usd,
        premium_bean_alias: pending.premium_bean_alias,
        decision_deadline: pending.decision_deadline,
      },
      pendingEscalationRecovered: true,
    };
    appendMessage(set, sessionId, message);
  },

  setProjectFilter: (filter: ProjectFilter) => {
    set({ projectFilter: filter, sessionsLoaded: false });
    get().loadSessions();
  },

  loadProjects: async () => {
    const projects = await api.listProjects();
    set({ projects });
  },

  createProject: async (name: string) => {
    await api.createProject(name);
    await get().loadProjects();
  },

  renameProject: async (projectId: number, name: string) => {
    await api.renameProject(projectId, name);
    await get().loadProjects();
    const filter = get().projectFilter;
    if (filter !== "all" && filter !== "default" && filter.id === projectId) {
      set({ projectFilter: { ...filter, name } });
    }
  },

  deleteProject: async (projectId: number) => {
    await api.deleteProject(projectId);
    await get().loadProjects();
    // The router moves this project's sessions to "default" - if it was
    // the active filter, fall back to "default" rather than pointing at
    // a project that no longer exists.
    const filter = get().projectFilter;
    if (filter !== "all" && filter !== "default" && filter.id === projectId) {
      get().setProjectFilter("default");
    } else {
      await get().loadSessions();
    }
  },

  renameSession: async (sessionId: string, title: string) => {
    await api.renameSession(sessionId, title);
    await get().loadSessions();
  },

  deleteSession: async (sessionId: string) => {
    await api.deleteSession(sessionId);
    if (get().activeSessionId === sessionId) {
      set({ activeSessionId: null });
    }
    await get().loadSessions();
  },

  setRememberChat: async (sessionId: string, rememberChat: boolean) => {
    const previous = get().sessions.find((s) => s.id === sessionId)?.remember_chat;
    set((state) => ({
      sessions: state.sessions.map((s) =>
        s.id === sessionId ? { ...s, remember_chat: rememberChat } : s
      ),
    }));
    try {
      await api.setRememberChat(sessionId, rememberChat);
    } catch (err) {
      if (previous !== undefined) {
        set((state) => ({
          sessions: state.sessions.map((s) =>
            s.id === sessionId ? { ...s, remember_chat: previous } : s
          ),
        }));
      }
      throw err;
    }
  },
}));

async function pollForRecoveredResult(
  set: (fn: (state: ChatState) => Partial<ChatState>) => void,
  get: () => ChatState,
  sessionId: string,
  requestId: string
): Promise<void> {
  for (let attempt = 0; attempt < RECOVERED_ESCALATION_POLL_MAX_ATTEMPTS; attempt += 1) {
    await new Promise((resolve) => setTimeout(resolve, RECOVERED_ESCALATION_POLL_INTERVAL_MS));

    const stored = await api.getSessionMessages(sessionId).catch(() => null);
    if (stored === null) continue;
    const assistantRow = stored.find((m) => m.role === "assistant" && m.request_id === requestId);
    if (assistantRow === undefined) continue;

    updateMessage(set, sessionId, {
      ...(get().messages[sessionId] ?? []).find((m) => m.requestId === requestId)!,
      content: assistantRow.content,
      isStreaming: false,
      beanAlias: assistantRow.bean_alias,
      costUsd: assistantRow.cost_usd,
      latencyMs: assistantRow.latency_ms,
      escalated: assistantRow.escalated ?? false,
      draftQuality: assistantRow.draft_quality ?? false,
    });
    return;
  }
}

function findPriorUserMessage(messages: ChatMessage[], assistantMessageId: string): ChatMessage | null {
  const index = messages.findIndex((m) => m.id === assistantMessageId);
  if (index <= 0) return null;
  for (let i = index - 1; i >= 0; i -= 1) {
    if (messages[i].role === "user") return messages[i];
  }
  return null;
}

function appendMessage(
  set: (fn: (state: ChatState) => Partial<ChatState>) => void,
  sessionId: string,
  message: ChatMessage
) {
  set((state) => ({
    messages: {
      ...state.messages,
      [sessionId]: [...(state.messages[sessionId] ?? []), message],
    },
  }));
}

function updateMessage(
  set: (fn: (state: ChatState) => Partial<ChatState>) => void,
  sessionId: string,
  message: ChatMessage
) {
  set((state) => ({
    messages: {
      ...state.messages,
      [sessionId]: (state.messages[sessionId] ?? []).map((m) => (m.id === message.id ? message : m)),
    },
  }));
}
