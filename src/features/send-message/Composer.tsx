import { Check, Circle, Send } from "lucide-react";
import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react";

import type { MessageBody, Question } from "@/entities/chat";
import "./composer.css";

interface ComposerProps {
    readonly question: Question | null;
    readonly disabled: boolean;
    readonly sending: boolean;
    readonly questionLabelId?: string;
    readonly onSend: (body: MessageBody, label: string) => Promise<boolean>;
}

const REFUSE_CODE = "refuse";

export function Composer({ question, disabled, sending, questionLabelId, onSend }: ComposerProps) {
    const [draft, setDraft] = useState("");
    const [selected, setSelected] = useState<readonly string[]>([]);
    const textarea = useRef<HTMLTextAreaElement>(null);
    const form = useRef<HTMLFormElement>(null);
    const canWrite = !question || question.free_text;
    const options = question?.options ?? [];
    const hasAnswerOptions = options.some((option) => option.code !== REFUSE_CODE);
    const multiple = question?.multiple ?? false;
    const text = canWrite ? draft.trim() : "";
    const valid = selected.length > 0 || Boolean(text);

    useEffect(() => {
        const input = textarea.current;
        if (input) {
            input.style.height = "auto";
            input.style.height = `${input.scrollHeight}px`;
        }
    }, [canWrite, draft, selected.length, sending]);

    function toggle(code: string) {
        setSelected((current) => {
            if (current.includes(code)) {
                return current.filter((item) => item !== code);
            }
            if (!multiple || code === REFUSE_CODE) {
                return [code];
            }
            return [...current.filter((item) => item !== REFUSE_CODE), code];
        });
    }

    async function send(body: MessageBody, label: string) {
        if (!disabled && (await onSend(body, label))) {
            setDraft("");
            setSelected([]);
        }
    }

    function submit(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();
        if (selected.length) {
            const labels = options.filter((option) => selected.includes(option.code));
            void send(
                { option_codes: labels.map((option) => option.code) },
                labels.map((option) => option.label).join("\n"),
            );
        } else if (text) {
            void send({ text }, text);
        }
    }

    function handleKey(event: KeyboardEvent<HTMLTextAreaElement>) {
        if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
            event.preventDefault();
            if (valid && !disabled) {
                form.current?.requestSubmit();
            }
        }
    }

    return (
        <form
            className={question ? "composer composer--question" : "composer"}
            ref={form}
            onSubmit={submit}
            aria-label="Ответ в диалоге"
            aria-describedby={questionLabelId}
        >
            {options.length > 0 && (
                <fieldset className="composer__fieldset" disabled={disabled}>
                    <legend>
                        {multiple ? "Можно выбрать несколько вариантов" : "Варианты ответа"}
                    </legend>
                    <div className="composer__options">
                        {options.map((option) => {
                            const checked = selected.includes(option.code);
                            return (
                                <button
                                    key={option.code}
                                    className="choice"
                                    type="button"
                                    aria-pressed={checked}
                                    onClick={() => toggle(option.code)}
                                >
                                    {checked ? (
                                        <Check size={15} aria-hidden />
                                    ) : (
                                        <Circle size={12} aria-hidden />
                                    )}
                                    {option.label}
                                </button>
                            );
                        })}
                    </div>
                </fieldset>
            )}
            <div className={canWrite ? "composer__bar" : "composer__bar composer__bar--choices"}>
                {canWrite && (
                    <textarea
                        ref={textarea}
                        rows={1}
                        aria-label="Ваше сообщение"
                        placeholder={
                            hasAnswerOptions
                                ? "Или ответьте своими словами…"
                                : "Напишите сообщение…"
                        }
                        value={sending || selected.length ? "" : draft}
                        readOnly={disabled}
                        onChange={(event) => {
                            setDraft(event.currentTarget.value);
                            setSelected([]);
                        }}
                        onKeyDown={handleKey}
                    />
                )}
                <button
                    className={
                        canWrite
                            ? "button button--primary composer__send"
                            : "button button--primary"
                    }
                    type="submit"
                    disabled={disabled || !valid}
                >
                    <Send size={17} aria-hidden />
                    <span className={canWrite ? "visually-hidden" : undefined}>Отправить</span>
                </button>
            </div>
        </form>
    );
}
