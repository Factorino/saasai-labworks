import { FileText } from "lucide-react";

import { Spinner } from "@/shared/ui";

interface FinishChatButtonProps {
    readonly disabled: boolean;
    readonly loading: boolean;
    readonly onFinish: () => Promise<boolean>;
}

export function FinishChatButton({ disabled, loading, onFinish }: FinishChatButtonProps) {
    return (
        <button
            className="button button--quiet session-action"
            title="Получить сводку"
            disabled={disabled}
            onClick={() => void onFinish()}
        >
            {loading ? <Spinner size={17} /> : <FileText size={17} aria-hidden />}
            <span>Получить сводку</span>
        </button>
    );
}
