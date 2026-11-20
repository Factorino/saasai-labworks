import { Bug, X } from "lucide-react";
import { useId, useRef } from "react";

import type { Summary, Term } from "@/entities/chat";

import { caseFacts, FACT_LABELS } from "./facts";
import "./inspect-summary.css";

const degreeFormat = new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 2 });

interface TermGroupProps {
    readonly label: string;
    readonly terms: readonly (Term & { readonly quote?: string })[];
}

function TermGroup({ label, terms }: TermGroupProps) {
    if (!terms.length) {
        return null;
    }
    return (
        <div className="summary-debug__term-group">
            <h4>{label}</h4>
            <ul className="summary-debug__list">
                {terms.map((term, index) => (
                    <li key={`${term.term}-${index}`}>
                        <div className="summary-debug__term">
                            <span>{term.name}</span>
                            <code>{term.term}</code>
                        </div>
                        {term.quote && <p className="muted">«{term.quote}»</p>}
                    </li>
                ))}
            </ul>
        </div>
    );
}

export function InspectSummary({ summary }: { readonly summary: Summary }) {
    const dialog = useRef<HTMLDialogElement>(null);
    const titleId = useId();
    const { manifestations, stressors, affected_domains } = summary.case;
    const facts = caseFacts(summary);
    const termGroups = [
        { label: FACT_LABELS.manifestations, terms: manifestations },
        { label: "Стрессоры", terms: stressors },
        { label: FACT_LABELS.affected_domains, terms: affected_domains },
        { label: "Кластеры", terms: summary.clusters },
    ];

    return (
        <>
            <button
                className="button button--quiet summary-debug__trigger"
                type="button"
                aria-haspopup="dialog"
                onClick={() => dialog.current?.showModal()}
            >
                <Bug size={16} aria-hidden />
                Отладка
            </button>

            <dialog ref={dialog} className="summary-debug" aria-labelledby={titleId}>
                <header className="summary-debug__header">
                    <h2 id={titleId}>Панель отладки</h2>
                    <button
                        className="icon-button"
                        type="button"
                        aria-label="Закрыть панель отладки"
                        autoFocus
                        onClick={() => dialog.current?.close()}
                    >
                        <X size={20} aria-hidden />
                    </button>
                </header>

                <div className="summary-debug__content">
                    <section className="summary-debug__result">
                        <h3>Уровень срочности</h3>
                        <strong>
                            {summary.level === null ? "Недостаточно данных" : `L${summary.level}`}
                        </strong>
                        {summary.crisis && <p>Кризисный сценарий</p>}
                    </section>

                    <section>
                        <h3>Сработавшие правила</h3>
                        {summary.explanation.length > 0 ? (
                            <ul className="summary-debug__list">
                                {summary.explanation.map(({ rule, explanation }) => (
                                    <li key={rule}>
                                        <code>{rule}</code>
                                        <p>{explanation}</p>
                                    </li>
                                ))}
                            </ul>
                        ) : (
                            <p className="muted">Нет сработавших правил</p>
                        )}
                    </section>

                    <section>
                        <h3>Сведения</h3>
                        {facts.length > 0 ? (
                            <dl className="summary-debug__facts">
                                {facts.map(([label, value]) => (
                                    <div key={label}>
                                        <dt>{label}</dt>
                                        <dd>{value}</dd>
                                    </div>
                                ))}
                            </dl>
                        ) : (
                            <p className="muted">Нет сведений</p>
                        )}
                    </section>

                    <section>
                        <h3>Термины онтологии</h3>
                        {termGroups.map((group) => (
                            <TermGroup key={group.label} {...group} />
                        ))}
                        {termGroups.every((group) => !group.terms.length) && (
                            <p className="muted">Нет извлечённых терминов</p>
                        )}
                    </section>

                    <section>
                        <h3>Степени принадлежности</h3>
                        {summary.approximations.length > 0 ? (
                            <ul className="summary-debug__list">
                                {summary.approximations.map(({ fact, confidence, text }) => (
                                    <li key={fact}>
                                        <div className="summary-debug__term">
                                            <span>{FACT_LABELS[fact]}</span>
                                            <code>{degreeFormat.format(confidence)}</code>
                                        </div>
                                        <p className="muted">{text}</p>
                                    </li>
                                ))}
                            </ul>
                        ) : (
                            <p className="muted">Нет приблизительных оценок</p>
                        )}
                    </section>
                </div>
            </dialog>
        </>
    );
}
