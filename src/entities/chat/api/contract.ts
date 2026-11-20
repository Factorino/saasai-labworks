// DTOs used by the client, as exposed in the FastAPI OpenAPI contract.
export type ChatStage = "story" | "clarifying" | "summary" | "crisis" | "finished";
export type UrgencyLevel = 0 | 1 | 2 | 3;
export type Referral = "emergency_medical_care" | "crisis_helpline" | "doctor_visit";
export type FactKind =
    | "manifestations"
    | "duration"
    | "frequency"
    | "impact"
    | "affected_domains"
    | "self_harm"
    | "sleep"
    | "appetite"
    | "energy"
    | "substance_use"
    | "goal";

type Scale = 0 | 1 | 2 | 3;
type SelfHarmScreening = "none" | "passive" | "active" | "plan" | "unknown";
type ChangeDirection = "unchanged" | "decreased" | "increased";

export interface Option {
    readonly code: string;
    readonly label: string;
}

export interface Question {
    readonly fact: FactKind;
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

export interface Term {
    readonly term: string;
    readonly name: string;
}

interface Evidence extends Term {
    readonly quote: string;
}

interface CaseDetails {
    readonly manifestations: readonly Evidence[];
    readonly stressors: readonly Evidence[];
    readonly unrecognized: readonly string[];
    readonly duration_weeks: number | null;
    readonly frequency: Scale | null;
    readonly impact: Scale | null;
    readonly affected_domains: readonly Term[];
    readonly self_harm: SelfHarmScreening | null;
    readonly sleep: ChangeDirection | null;
    readonly appetite: ChangeDirection | null;
    readonly energy: ChangeDirection | null;
    readonly substance_use: boolean | null;
    readonly goal: string | null;
    readonly refused: readonly FactKind[];
}

interface Rule {
    readonly rule: string;
    readonly explanation: string;
}

interface Approximation {
    readonly fact: FactKind;
    readonly confidence: number;
    readonly text: string;
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
    readonly clusters: readonly Term[];
    readonly explanation: readonly Rule[];
    readonly missing: readonly FactKind[];
    readonly approximations: readonly Approximation[];
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
