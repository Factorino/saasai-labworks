import { useEffect, useState } from "react";

import { ChatMessage } from "@/entities/chat";

const REPLY_STEPS = ["Читаю сообщение", "Обдумываю ответ", "Формулирую ответ"] as const;
const SUMMARY_STEPS = ["Собираю сводку", "Упорядочиваю ответы", "Формулирую сводку"] as const;
const STEP_INTERVAL_MS = 1450;

export function PendingReply({ finishing }: { readonly finishing: boolean }) {
    const steps = finishing ? SUMMARY_STEPS : REPLY_STEPS;
    const [step, setStep] = useState(0);

    useEffect(() => {
        if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
            return;
        }
        const timer = window.setInterval(() => {
            setStep((previous) => (previous + 1) % steps.length);
        }, STEP_INTERVAL_MS);
        return () => window.clearInterval(timer);
    }, [steps]);

    return (
        <ChatMessage role="assistant">
            <span className="visually-hidden" role="status">
                {finishing ? "Готовлю сводку" : "Готовлю ответ"}
            </span>
            <span className="pending-reply" key={step} aria-hidden>
                {steps[step]}…
            </span>
        </ChatMessage>
    );
}
