import { AlertCircle, Check, ClipboardCopy, FileText, Phone } from "lucide-react";
import { useState } from "react";

import type { Reply, Summary } from "@/entities/chat";
import { InspectSummary } from "@/features/inspect-summary";

import { specialistText } from "./specialist-text";
import "./summary.css";

function isUrgent(reply: Reply, summary: Summary): boolean {
    return (
        reply.stage === "crisis" ||
        summary.crisis ||
        summary.level === 3 ||
        summary.referrals.some(
            ({ referral }) =>
                referral === "emergency_medical_care" || referral === "crisis_helpline",
        )
    );
}

function sourceLink(value: string): string | undefined {
    try {
        const url = new URL(value);
        if (url.protocol === "https:" || url.protocol === "http:") {
            return url.href;
        }
    } catch {
        return undefined;
    }
}

function SpecialistRequest({ text }: { readonly text: string }) {
    const [status, setStatus] = useState<"idle" | "copied" | "failed">("idle");

    async function copy() {
        try {
            await navigator.clipboard.writeText(text);
            setStatus("copied");
        } catch {
            setStatus("failed");
        }
    }

    return (
        <section className="summary__section">
            <div className="summary__section-heading">
                <h3>Что сказать специалисту</h3>
                <button
                    className="text-button copy-button"
                    type="button"
                    onClick={() => void copy()}
                >
                    {status === "copied" ? (
                        <Check size={16} aria-hidden />
                    ) : (
                        <ClipboardCopy size={16} aria-hidden />
                    )}
                    {status === "copied" ? "Скопировано" : "Скопировать"}
                </button>
            </div>
            <blockquote className="summary__request">{text}</blockquote>
            <span className="visually-hidden" role="status">
                {status === "copied" ? "Текст скопирован" : ""}
            </span>
            {status === "failed" && (
                <p className="muted" role="status">
                    Выделите текст и скопируйте его вручную.
                </p>
            )}
        </section>
    );
}

interface SummaryCardProps {
    readonly reply: Reply;
    readonly summary: Summary;
    readonly id: string;
}

export function SummaryCard({ reply, summary, id }: SummaryCardProps) {
    const urgent = isUrgent(reply, summary);

    return (
        <div className="summary-stack">
            {(urgent || summary.helplines.length > 0) && (
                <section
                    className={urgent ? "help-card help-card--urgent" : "help-card"}
                    aria-labelledby={`${id}-help`}
                >
                    <h2 id={`${id}-help`}>
                        <AlertCircle size={20} aria-hidden />
                        {urgent ? "Срочная помощь" : "Контакты помощи"}
                    </h2>
                    {reply.message && <p className="message-text">{reply.message}</p>}
                    {urgent &&
                        summary.referrals.map((referral) => (
                            <p key={referral.referral}>{referral.text}</p>
                        ))}
                    {summary.helplines.length > 0 && (
                        <ul className="helplines">
                            {summary.helplines.map((line) => (
                                <li key={line.name}>
                                    <span>
                                        <strong>{line.name}</strong>
                                        {line.note && <small>{line.note}</small>}
                                    </span>
                                    <a href={`tel:${line.phone.replace(/[^+\d]/g, "")}`}>
                                        <Phone size={15} aria-hidden />
                                        {line.phone}
                                    </a>
                                </li>
                            ))}
                        </ul>
                    )}
                </section>
            )}
            <section className="summary" aria-labelledby={`${id}-title`}>
                <header className="summary__heading">
                    <FileText size={21} aria-hidden />
                    <h2 id={`${id}-title`}>Сводка диалога</h2>
                    <InspectSummary summary={summary} />
                </header>
                <div className="summary__section">
                    {summary.phrase && <p className="summary__phrase">{summary.phrase}</p>}
                    <p className="message-text">{summary.description}</p>
                </div>
                <section className="summary__section">
                    <h3>Следующие шаги</h3>
                    <p>{summary.specialist}</p>
                    {!urgent &&
                        summary.referrals.map((referral) => (
                            <p key={referral.referral}>{referral.text}</p>
                        ))}
                    {summary.support_others && <p>{summary.support_others}</p>}
                </section>
                <SpecialistRequest text={specialistText(summary)} />
                {summary.practices.length > 0 && (
                    <section className="summary__section">
                        <h3>Практики самопомощи</h3>
                        <div className="practice-list">
                            {summary.practices.map((practice) => (
                                <details key={practice.term} className="practice">
                                    <summary>{practice.name}</summary>
                                    <p>{practice.description}</p>
                                    <ol>
                                        {practice.guide.steps.map((step) => (
                                            <li key={step}>{step}</li>
                                        ))}
                                    </ol>
                                    {(practice.cautions.length > 0 ||
                                        practice.guide.limits.length > 0) && (
                                        <div className="practice__limits">
                                            <strong>Что важно учесть</strong>
                                            {practice.cautions.length > 0 && (
                                                <p>
                                                    {practice.cautions
                                                        .map((item) => item.name)
                                                        .join(", ")}
                                                </p>
                                            )}
                                            {practice.guide.limits.map((limit) => (
                                                <p key={limit}>{limit}</p>
                                            ))}
                                        </div>
                                    )}
                                    {practice.guide.sources.length > 0 && (
                                        <ul className="practice__sources">
                                            {practice.guide.sources.map((source) => {
                                                const url = sourceLink(source.url);
                                                return (
                                                    <li key={source.url}>
                                                        {url ? (
                                                            <a
                                                                href={url}
                                                                target="_blank"
                                                                rel="noreferrer"
                                                            >
                                                                {source.title}
                                                            </a>
                                                        ) : (
                                                            source.title
                                                        )}
                                                    </li>
                                                );
                                            })}
                                        </ul>
                                    )}
                                </details>
                            ))}
                        </div>
                    </section>
                )}
                <footer className="summary__footer">{summary.disclaimer}</footer>
            </section>
        </div>
    );
}
