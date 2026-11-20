import { useEffect, useReducer, useRef } from "react";

import { HttpError } from "@/shared/api";

import { deleteChat, finishChat, getSummary, postMessage, startChat } from "../api/chat";
import type { MessageBody } from "../api/contract";
import {
    chatReducer,
    INITIAL_CHAT_STATE,
    type ChatAction,
    type ChatOperation,
    type PendingChatOperation,
} from "./session";

function isMissingChat(error: unknown): boolean {
    return (
        error instanceof HttpError &&
        error.status === 404 &&
        error.code === "not_found_error" &&
        error.entity === "Chat"
    );
}

function describeError(error: unknown, operation: ChatOperation): string {
    if (error instanceof HttpError) {
        if (isMissingChat(error)) {
            return "Сессия больше недоступна. Удалите диалог с экрана, чтобы начать заново.";
        }
        if (error.status === 409) {
            return "Это действие недоступно на текущем этапе диалога.";
        }
        if (error.status === 422) {
            return "Сервис не принял ответ. Проверьте текст или выбранные варианты.";
        }
        if (error.status === 403) {
            return "Для начала диалога требуется согласие на обработку данных.";
        }
    }
    if (operation === "delete") {
        return "Не удалось удалить диалог. Проверьте подключение и попробуйте ещё раз.";
    }
    return "Сервис временно недоступен. Проверьте подключение и попробуйте ещё раз.";
}

export function useChatSession() {
    const [state, dispatch] = useReducer(chatReducer, INITIAL_CHAT_STATE);
    const currentRequest = useRef<AbortController | null>(null);
    const chatId = state.session?.chat.id;

    useEffect(() => () => currentRequest.current?.abort(), []);

    async function run(
        operation: PendingChatOperation,
        task: (signal: AbortSignal) => Promise<ChatAction>,
    ): Promise<boolean> {
        if (currentRequest.current) {
            return false;
        }

        const controller = new AbortController();
        currentRequest.current = controller;
        dispatch({ type: "request", operation });

        try {
            const action = await task(controller.signal);
            if (controller.signal.aborted) {
                return false;
            }
            dispatch(action);
            return true;
        } catch (error) {
            if (!controller.signal.aborted) {
                dispatch({ type: "failure", message: describeError(error, operation.kind) });
            }
            return false;
        } finally {
            currentRequest.current = null;
        }
    }

    function start(): Promise<boolean> {
        return run({ kind: "start" }, async (signal) => ({
            type: "started",
            response: await startChat(signal),
        }));
    }

    function send(body: MessageBody, userText: string): Promise<boolean> {
        if (!chatId) {
            return Promise.resolve(false);
        }
        return run({ kind: "send", text: userText }, async (signal) => {
            const { reply } = await postMessage(chatId, body, signal);
            return { type: "replied", reply };
        });
    }

    function finish(): Promise<boolean> {
        if (!chatId) {
            return Promise.resolve(false);
        }
        return run({ kind: "finish" }, async (signal) => {
            const { reply } = await finishChat(chatId, signal);
            return { type: "replied", reply };
        });
    }

    function refreshSummary(): Promise<boolean> {
        if (!chatId) {
            return Promise.resolve(false);
        }
        return run({ kind: "summary" }, async (signal) => {
            const { summary } = await getSummary(chatId, signal);
            return { type: "summary", summary };
        });
    }

    function remove(): Promise<boolean> {
        if (!chatId) {
            return Promise.resolve(false);
        }
        return run({ kind: "delete" }, async (signal) => {
            try {
                await deleteChat(chatId, signal);
            } catch (error) {
                if (!isMissingChat(error)) {
                    throw error;
                }
            }
            return { type: "deleted" };
        });
    }

    return { ...state, start, send, finish, refreshSummary, remove };
}
