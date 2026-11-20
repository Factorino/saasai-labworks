import { Sprout, UserRound } from "lucide-react";
import type { ReactNode } from "react";

import { SERVICE_NAME } from "@/shared/config";
import "./chat-message.css";

export function ServiceMark({ large = false }: { readonly large?: boolean }) {
    return (
        <span className={large ? "service-mark service-mark--large" : "service-mark"} aria-hidden>
            <Sprout strokeWidth={1.8} />
        </span>
    );
}

export function ChatMessage({
    role,
    children,
    wide = false,
}: {
    readonly role: "assistant" | "user";
    readonly children: ReactNode;
    readonly wide?: boolean;
}) {
    return (
        <div className={`message message--${role}${wide ? " message--wide" : ""}`}>
            {role === "assistant" ? (
                <ServiceMark />
            ) : (
                <span className="message__user-mark" aria-hidden>
                    <UserRound size={17} strokeWidth={1.8} />
                </span>
            )}
            <div className="message__content">
                <span className="message__author">
                    {role === "assistant" ? SERVICE_NAME : "Вы"}
                </span>
                <div className="message__bubble">{children}</div>
            </div>
        </div>
    );
}
