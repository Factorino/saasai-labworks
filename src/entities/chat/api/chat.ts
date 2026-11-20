import { request } from "@/shared/api";

import type { MessageBody, ReplyResponse, StartChatResponse, SummaryResponse } from "./contract";

function chatPath(id: string): string {
    return `/chats/${encodeURIComponent(id)}`;
}

export function startChat(signal: AbortSignal): Promise<StartChatResponse> {
    return request("/chats", {
        method: "POST",
        body: JSON.stringify({ consent: true, language: "ru" }),
        signal,
    });
}

export function postMessage(
    id: string,
    body: MessageBody,
    signal: AbortSignal,
): Promise<ReplyResponse> {
    return request(`${chatPath(id)}/messages`, {
        method: "POST",
        body: JSON.stringify(body),
        signal,
    });
}

export function finishChat(id: string, signal: AbortSignal): Promise<ReplyResponse> {
    return request(`${chatPath(id)}/finish`, { method: "POST", signal });
}

export function getSummary(id: string, signal: AbortSignal): Promise<SummaryResponse> {
    return request(`${chatPath(id)}/summary`, { method: "GET", signal });
}

export function deleteChat(id: string, signal: AbortSignal): Promise<void> {
    return request(chatPath(id), { method: "DELETE", signal }, "empty");
}
