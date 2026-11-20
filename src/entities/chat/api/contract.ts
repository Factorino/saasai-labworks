// DTOs used by the client, as exposed in the FastAPI OpenAPI contract.
export type ChatStage = "story" | "clarifying" | "summary" | "crisis" | "finished";
export type UrgencyLevel = 0 | 1 | 2 | 3;
export type Referral = "emergency_medical_care" | "crisis_helpline" | "doctor_visit";

export interface Option {
    readonly code: string;
    readonly label: string;
}

export interface Question {
    readonly fact: string;
    readonly text: string;
    readonly options: readonly Option[];
    readonly multiple: boolean;
    readonly free_text: boolean;
}

interface Helpline {
    readonly name: string;
    readonly phone: string;
    readonly note?: string;
}

interface ReferralAdvice {
    readonly referral: Referral;
    readonly text: string;
}

interface Term {
    readonly term: string;
    readonly name: string;
}

interface CaseDetails {
    readonly manifestations: readonly Term[];
    readonly stressors: readonly Term[];
    readonly unrecognized: readonly string[];
    readonly duration_weeks: number | null;
    readonly affected_domains: readonly Term[];
    readonly goal: string | null;
}

interface Practice {
    readonly term: string;
    readonly name: string;
    readonly description: string;
    readonly guide: {
        readonly steps: readonly string[];
        readonly limits: readonly string[];
        readonly sources: readonly { readonly title: string; readonly url: string }[];
    };
    readonly cautions: readonly Term[];
}

export interface Summary {
    readonly level: UrgencyLevel | null;
    readonly phrase: string | null;
    readonly description: string;
    readonly specialist_request: string;
    readonly specialist: string;
    readonly crisis: boolean;
    readonly referrals: readonly ReferralAdvice[];
    readonly helplines: readonly Helpline[];
    readonly support_others: string | null;
    readonly practices: readonly Practice[];
    readonly case: CaseDetails;
    readonly disclaimer: string;
}

export interface Reply {
    readonly stage: ChatStage;
    readonly message: string | null;
    readonly question: Question | null;
    readonly summary: Summary | null;
}

export interface Chat {
    readonly id: string;
    readonly language: string;
    readonly stage: ChatStage;
    readonly created_at: string;
}

export type MessageBody =
    | { readonly text: string; readonly option_codes?: never }
    | { readonly option_codes: readonly string[]; readonly text?: never };

export interface StartChatResponse {
    readonly chat: Chat;
    readonly message: string;
}

export interface ReplyResponse {
    readonly reply: Reply;
}

export interface SummaryResponse {
    readonly summary: Summary;
}
