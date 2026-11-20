import { Check, Circle, Send } from "lucide-react";
import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react";

import type { MessageBody, Question } from "@/entities/chat";
import { Spinner } from "@/shared/ui";
import "./composer.css";

interface ComposerProps {
    readonly question: Question | null;
    readonly disabled: boolean;
    readonly sending: boolean;
    readonly onSend: (body: MessageBody, label: string) => Promise<boolean>;
}

const REFUSE_CODE = "refuse";

export function Composer({ question, disabled, sending, onSend }: ComposerProps) {
    const [draft, setDraft] = useState("");
    const [selection, setSelection] = useState<{
        question: Question;
        codes: readonly string[];
    } | null>(null);
    const selected = selection?.question === question ? selection.codes : [];
    const textarea = useRef<HTMLTextAreaElement>(null);
    const form = useRef<HTMLFormElement>(null);
    const canWrite = !question || question.free_text;
    const options = question?.options.filter((option) => option.code !== REFUSE_CODE) ?? [];
    const refusal = question?.options.find((option) => option.code === REFUSE_CODE);
    const multiple = question?.multiple ?? false;
    const text = canWrite ? draft.trim() : "";
    const valid = selected.length > 0 || Boolean(text);

    useEffect(() => {
        const input = textarea.current;
        if (input) {
            input.style.height = "auto";
            input.style.height = `${input.scrollHeight}px`;
        }
    }, [canWrite, draft, selected.length]);

    function toggle(code: string) {
        if (!question) {
            return;
        }
        const codes = selected.includes(code)
            ? selected.filter((item) => item !== code)
            : multiple
              ? [...selected, code]
              : [code];
        setSelection({ question, codes });
    }

    async function send(body: MessageBody, label: string) {
        if (!disabled && (await onSend(body, label))) {
            setDraft("");
            setSelection(null);
        }
    }

    function submit(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();
        if (selected.length) {
            const labels = options.filter((option) => selected.includes(option.code));
            void send(
                { option_codes: labels.map((option) => option.code) },
                labels.map((option) => option.label).join(", "),
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
            className="composer"
            ref={form}
            onSubmit={submit}
            aria-label="Ответ в диалоге"
            aria-describedby={question ? "current-chat-question" : undefined}
        >
            {options.length > 0 && (
                <fieldset className="composer__fieldset" disabled={disabled}>
                    <legend>
                        {multiple ? "Можно выбрать несколько вариантов" : "Выберите вариант"}
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
                            options.length ? "Или ответьте своими словами…" : "Напишите сообщение…"
                        }
                        value={selected.length ? "" : draft}
                        readOnly={disabled}
                        onChange={(event) => {
                            setDraft(event.currentTarget.value);
                            setSelection(null);
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
                    {sending ? <Spinner /> : <Send size={17} aria-hidden />}
                    <span className={canWrite ? "visually-hidden" : undefined}>Отправить</span>
                </button>
            </div>
            {refusal && (
                <button
                    className="text-button composer__skip"
                    type="button"
                    disabled={disabled}
                    onClick={() => void send({ option_codes: [refusal.code] }, refusal.label)}
                >
                    {refusal.label}
                </button>
            )}
        </form>
    );
}
