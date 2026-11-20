import { useLayoutEffect, useRef } from "react";

import {
    ChatMessage,
    type ChatEntry,
    type MessageBody,
    type PendingChatOperation,
} from "@/entities/chat";
import { Composer } from "@/features/send-message";

import { PendingReply } from "./PendingReply";
import { SummaryCard } from "./SummaryCard";
import "./thread.css";

interface ChatThreadProps {
    readonly entries: readonly ChatEntry[];
    readonly pending: PendingChatOperation | null;
    readonly onSend: (body: MessageBody, label: string) => Promise<boolean>;
}

function summaryTarget(index: number): string {
    return `chat-summary-${index}`;
}

function scrollToEntry(target: Element, thread: Element): void {
    const offset = target.getBoundingClientRect().top - thread.getBoundingClientRect().top;
    const padding = Number.parseFloat(getComputedStyle(thread).scrollPaddingBlockStart) || 0;
    thread.scrollTop += offset - padding;
}

export function showSummary(index: number, focus = false): void {
    const target = document.getElementById(summaryTarget(index));
    const thread = target?.closest(".thread");
    if (!target || !thread) {
        return;
    }
    if (focus) {
        target.focus({ preventScroll: true });
    }
    scrollToEntry(target, thread);
}

export function ChatThread({ entries, pending, onSend }: ChatThreadProps) {
    const thread = useRef<HTMLDivElement>(null);
    const latest = entries.at(-1);
    const newestSummary = latest?.kind === "reply" && Boolean(latest.reply.summary);
    const waiting = pending?.kind === "send" || pending?.kind === "finish";
    const visibleEntries: readonly ChatEntry[] =
        pending?.kind === "send"
            ? [...entries, { kind: "message", role: "user", text: pending.text }]
            : entries;

    useLayoutEffect(() => {
        const element = thread.current;
        if (!element) {
            return;
        }
        if (!waiting && newestSummary) {
            showSummary(entries.length - 1);
            return;
        }
        const activeCard = element.querySelector("[data-active-question]");
        if (activeCard && activeCard.getBoundingClientRect().height > element.clientHeight - 32) {
            scrollToEntry(activeCard, element);
        } else {
            element.scrollTop = element.scrollHeight;
        }
    }, [entries.length, newestSummary, waiting]);

    return (
        <div className="thread" ref={thread}>
            <div
                className="thread__content"
                role="log"
                aria-label="Переписка"
                aria-relevant="additions"
            >
                {visibleEntries.map((entry, index) => {
                    if (entry.kind === "message") {
                        return (
                            <ChatMessage key={index} role={entry.role}>
                                <p className="message-text">{entry.text}</p>
                            </ChatMessage>
                        );
                    }

                    const { reply } = entry;
                    if (reply.summary) {
                        const target = summaryTarget(index);
                        return (
                            <div key={index} id={target} tabIndex={-1} className="thread__summary">
                                <SummaryCard reply={reply} summary={reply.summary} id={target} />
                            </div>
                        );
                    }

                    const question = reply.question;
                    const active = question !== null && index === entries.length - 1;
                    const questionId = `chat-question-${index}`;
                    return (
                        <ChatMessage key={index} role="assistant" wide={active && !waiting}>
                            {reply.message && <p className="message-text">{reply.message}</p>}
                            {question && (
                                <div data-active-question={active && !waiting ? "" : undefined}>
                                    <p className="message-text" id={questionId}>
                                        {question.text}
                                    </p>
                                    {active && (
                                        <div hidden={waiting}>
                                            <Composer
                                                question={question}
                                                questionLabelId={questionId}
                                                disabled={pending !== null}
                                                sending={pending?.kind === "send"}
                                                onSend={onSend}
                                            />
                                        </div>
                                    )}
                                </div>
                            )}
                        </ChatMessage>
                    );
                })}
                {waiting && <PendingReply finishing={pending?.kind === "finish"} />}
            </div>
        </div>
    );
}
