import type { Chat, Reply, StartChatResponse, Summary } from "../api/contract";

export type ChatEntry =
    | { readonly kind: "message"; readonly role: "assistant" | "user"; readonly text: string }
    | { readonly kind: "reply"; readonly reply: Reply };

export interface ChatSession {
    readonly chat: Chat;
    readonly entries: readonly ChatEntry[];
}

export type ChatOperation = "start" | "send" | "finish" | "summary" | "delete";

export type PendingChatOperation =
    | { readonly kind: Exclude<ChatOperation, "send"> }
    | { readonly kind: "send"; readonly text: string };

export interface ChatState {
    readonly session: ChatSession | null;
    readonly pending: PendingChatOperation | null;
    readonly error: string | null;
}

export type ChatAction =
    | { readonly type: "request"; readonly operation: PendingChatOperation }
    | { readonly type: "failure"; readonly message: string }
    | { readonly type: "started"; readonly response: StartChatResponse }
    | { readonly type: "replied"; readonly reply: Reply }
    | { readonly type: "summary"; readonly summary: Summary }
    | { readonly type: "deleted" };

export const INITIAL_CHAT_STATE: ChatState = { session: null, pending: null, error: null };

export function chatReducer(state: ChatState, action: ChatAction): ChatState {
    switch (action.type) {
        case "request":
            return { ...state, pending: action.operation, error: null };
        case "failure":
            return { ...state, pending: null, error: action.message };
        case "started":
            return {
                ...INITIAL_CHAT_STATE,
                session: {
                    chat: action.response.chat,
                    entries: [
                        { kind: "message", role: "assistant", text: action.response.message },
                    ],
                },
            };
        case "replied": {
            if (!state.session) {
                return state;
            }
            const entries: ChatEntry[] = [...state.session.entries];
            if (state.pending?.kind === "send") {
                entries.push({ kind: "message", role: "user", text: state.pending.text });
            }
            entries.push({ kind: "reply", reply: action.reply });
            return {
                ...INITIAL_CHAT_STATE,
                session: { chat: { ...state.session.chat, stage: action.reply.stage }, entries },
            };
        }
        case "summary": {
            if (!state.session) {
                return state;
            }
            const entries = [...state.session.entries];
            const index = latestSummaryIndex(entries);
            const entry = entries[index];
            if (entry?.kind === "reply") {
                entries[index] = { ...entry, reply: { ...entry.reply, summary: action.summary } };
            }
            return { ...INITIAL_CHAT_STATE, session: { ...state.session, entries } };
        }
        case "deleted":
            return INITIAL_CHAT_STATE;
    }
}

export function latestSummaryIndex(entries: readonly ChatEntry[]): number {
    for (let index = entries.length - 1; index >= 0; index -= 1) {
        const entry = entries[index];
        if (entry?.kind === "reply" && entry.reply.summary) {
            return index;
        }
    }
    return -1;
}
