import { ShieldCheck } from "lucide-react";
import { useState, type FormEvent } from "react";

import { ServiceMark } from "@/entities/chat";
import { ErrorMessage, Spinner } from "@/shared/ui";
import "./start-chat.css";

interface StartChatProps {
    readonly loading: boolean;
    readonly error: string | null;
    readonly onStart: () => Promise<boolean>;
}

export function StartChat({ loading, error, onStart }: StartChatProps) {
    const [consent, setConsent] = useState(false);

    function submit(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();
        if (consent && !loading) {
            void onStart();
        }
    }

    return (
        <section className="welcome" aria-labelledby="welcome-title">
            <div className="welcome__intro">
                <ServiceMark large />
                <h1 id="welcome-title">Расскажите, что вас беспокоит</h1>
                <p>
                    Анамнез задаст несколько вопросов и соберёт сводку, с которой можно обратиться
                    к психологу.
                </p>
            </div>
            <form className="welcome__form" onSubmit={submit}>
                <label className="consent">
                    <input
                        type="checkbox"
                        checked={consent}
                        disabled={loading}
                        onChange={(event) => setConsent(event.currentTarget.checked)}
                    />
                    <span>Согласен на обработку ответов для формирования сводки.</span>
                </label>
                <button
                    className="button button--primary"
                    type="submit"
                    disabled={!consent || loading}
                >
                    {loading && <Spinner />}
                    {loading ? "Открываем диалог…" : "Начать диалог"}
                </button>
                {error && <ErrorMessage message={error} />}
            </form>
            <p className="welcome__note">
                <ShieldCheck size={17} aria-hidden />
                Сводка не является диагнозом и не заменяет консультацию.
            </p>
        </section>
    );
}
