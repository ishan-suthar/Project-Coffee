import { create } from "zustand";
import { v4 as uuidv4 } from "@/lib/uuid";
import * as api from "@/lib/api";
import type { Rating, SessionSummary } from "@/lib/events";
import {
  AttachmentSummary,
  ChatMessage,
  newAssistantMessage,
  newUserMessage,
  reduceEventIntoMessage,
} from "@/lib/chat";

const DEFAULT_PROJECT = "default";

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
}

interface ChatState {
  project: string;
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
}

export const useChatStore = create<ChatState>((set, get) => ({
  project: DEFAULT_PROJECT,
  activeSessionId: null,
  sessions: [],
  sessionsLoaded: false,
  messages: {},
  activeRequestId: null,
  abortController: null,

  loadSessions: async () => {
    const sessions = await api.listSessions(get().project);
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
      // Session history has no attachment persistence yet (non-goal -
      // docs/design/attachments-design.md Section 11).
      attachments: [],
    }));
    set((state) => ({ messages: { ...state.messages, [sessionId]: messages } }));
  },

  startNewSession: () => {
    set({ activeSessionId: null });
  },

  sendPrompt: async (prompt: string, options: SendPromptOptions = {}) => {
    let sessionId = get().activeSessionId;
    if (sessionId === null) {
      const created = await api.createSession(get().project);
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
}));

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
