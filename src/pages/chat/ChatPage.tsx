import { FileText, LockKeyhole } from "lucide-react";
import { useEffect, useRef } from "react";

import { latestSummaryIndex, ServiceMark, useChatSession } from "@/entities/chat";
import { DeleteChatButton } from "@/features/delete-chat";
import { FinishChatButton } from "@/features/finish-chat";
import { Composer } from "@/features/send-message";
import { StartChat } from "@/features/start-chat";
import { ThemeToggle } from "@/features/toggle-theme";
import { ErrorMessage, Spinner } from "@/shared/ui";
import { ChatThread, showSummary } from "@/widgets/chat-thread";
import "./chat-page.css";

export function ChatPage() {
    const { session, pending, error, start, send, finish, refreshSummary, remove } =
        useChatSession();
    const main = useRef<HTMLElement>(null);
    const stage = session?.chat.stage;
    const chatId = session?.chat.id;
    const previouslyActive = useRef(false);
    const latest = session?.entries.at(-1);
    const question = latest?.kind === "reply" ? latest.reply.question : null;
    const summaryIndex = session ? latestSummaryIndex(session.entries) : -1;
    const busy = pending !== null;

    useEffect(() => {
        if (chatId || previouslyActive.current) {
            main.current?.focus({ preventScroll: true });
        }
        previouslyActive.current = Boolean(chatId);
    }, [chatId]);

    function openSummary() {
        showSummary(summaryIndex, true);
        void refreshSummary();
    }

    return (
        <div className="app-shell">
            <header className="app-header">
                <div className="app-header__content">
                    <div className="brand">
                        <ServiceMark />
                        <span>Анамнез</span>
                    </div>
                    <div className="app-header__actions">
                        {(stage === "story" || stage === "clarifying") && (
                            <FinishChatButton
                                disabled={busy}
                                loading={pending === "finish"}
                                onFinish={finish}
                            />
                        )}
                        {summaryIndex >= 0 && (
                            <button
                                className="button button--quiet session-action"
                                type="button"
                                disabled={busy}
                                onClick={openSummary}
                            >
                                {pending === "summary" ? (
                                    <Spinner size={17} />
                                ) : (
                                    <FileText size={17} aria-hidden />
                                )}
                                <span>Сводка</span>
                            </button>
                        )}
                        {session && (
                            <DeleteChatButton
                                disabled={busy}
                                loading={pending === "delete"}
                                onDelete={remove}
                            />
                        )}
                        <ThemeToggle />
                    </div>
                </div>
            </header>
            {session ? (
                <main className="chat" ref={main} tabIndex={-1} aria-labelledby="chat-heading">
                    <h1 id="chat-heading" className="visually-hidden">
                        Диалог с Анамнезом
                    </h1>
                    <ChatThread entries={session.entries} />
                    <div className="chat-input">
                        <div className="chat-input__content">
                            {error && <ErrorMessage message={error} />}
                            {(pending === "send" || pending === "finish") && (
                                <p className="chat-input__status" role="status">
                                    <Spinner size={15} />
                                    {pending === "finish" ? "Собираем сводку…" : "Готовим ответ…"}
                                </p>
                            )}
                            {stage !== "finished" && (
                                <Composer
                                    question={question}
                                    disabled={busy}
                                    sending={pending === "send"}
                                    onSend={send}
                                />
                            )}
                        </div>
                    </div>
                </main>
            ) : (
                <main
                    className="welcome-page"
                    ref={main}
                    tabIndex={-1}
                    aria-labelledby="welcome-title"
                >
                    <StartChat loading={pending === "start"} error={error} onStart={start} />
                </main>
            )}
            {!session && (
                <footer className="app-footer">
                    <LockKeyhole size={14} aria-hidden />
                    История не сохраняется в браузере
                </footer>
            )}
        </div>
    );
}
