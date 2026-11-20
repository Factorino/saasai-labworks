import { useLayoutEffect, useRef } from "react";

import { ChatMessage, type ChatEntry } from "@/entities/chat";

import { SummaryCard } from "./SummaryCard";
import "./thread.css";

interface ChatThreadProps {
    readonly entries: readonly ChatEntry[];
}

function summaryTarget(index: number): string {
    return `chat-summary-${index}`;
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
    const offset = target.getBoundingClientRect().top - thread.getBoundingClientRect().top;
    const padding = Number.parseFloat(getComputedStyle(thread).scrollPaddingBlockStart) || 0;
    thread.scrollTop += offset - padding;
}

export function ChatThread({ entries }: ChatThreadProps) {
    const thread = useRef<HTMLDivElement>(null);
    const latest = entries.at(-1);
    const newestSummary = latest?.kind === "reply" && Boolean(latest.reply.summary);

    useLayoutEffect(() => {
        const element = thread.current;
        if (newestSummary) {
            showSummary(entries.length - 1);
        } else if (element) {
            element.scrollTop = element.scrollHeight;
        }
    }, [entries.length, newestSummary]);

    return (
        <div className="thread" ref={thread}>
            <div
                className="thread__content"
                role="log"
                aria-label="Переписка"
                aria-relevant="additions"
            >
                {entries.map((entry, index) => {
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

                    return (
                        <ChatMessage key={index} role="assistant">
                            {reply.message && <p className="message-text">{reply.message}</p>}
                            {reply.question && (
                                <p className="message-text">{reply.question.text}</p>
                            )}
                        </ChatMessage>
                    );
                })}
            </div>
        </div>
    );
}
