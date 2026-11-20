import { Trash2 } from "lucide-react";
import { useRef } from "react";

import { Spinner } from "@/shared/ui";
import "./delete-chat.css";

interface DeleteChatButtonProps {
    readonly disabled: boolean;
    readonly loading: boolean;
    readonly onDelete: () => Promise<boolean>;
}

export function DeleteChatButton({ disabled, loading, onDelete }: DeleteChatButtonProps) {
    const dialog = useRef<HTMLDialogElement>(null);

    function confirm() {
        dialog.current?.close();
        void onDelete();
    }

    return (
        <>
            <button
                type="button"
                className="icon-button delete-button"
                aria-label="Удалить диалог"
                title="Удалить диалог"
                disabled={disabled}
                onClick={() => dialog.current?.showModal()}
            >
                {loading ? <Spinner /> : <Trash2 size={18} aria-hidden />}
            </button>
            <dialog ref={dialog} className="delete-dialog" aria-labelledby="delete-title">
                <h2 id="delete-title">Удалить диалог?</h2>
                <p>Переписка и сводка будут удалены.</p>
                <div className="delete-dialog__actions">
                    <button
                        type="button"
                        className="button button--quiet"
                        autoFocus
                        onClick={() => dialog.current?.close()}
                    >
                        Отмена
                    </button>
                    <button type="button" className="button button--danger" onClick={confirm}>
                        Удалить
                    </button>
                </div>
            </dialog>
        </>
    );
}
