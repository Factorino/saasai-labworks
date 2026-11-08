from anamnesis.application.dto.base import DTO
from anamnesis.domain.enums.change_direction import ChangeDirection
from anamnesis.domain.enums.crisis_category import CrisisCategory
from anamnesis.domain.enums.fact_kind import FactKind
from anamnesis.domain.enums.frequency import Frequency
from anamnesis.domain.enums.impact_degree import ImpactDegree
from anamnesis.domain.enums.referral import Referral
from anamnesis.domain.enums.self_harm_screening import SelfHarmScreening
from anamnesis.domain.enums.urgency_level import UrgencyLevel
from anamnesis.domain.types import RuleId, TermId


class TermView(DTO):
    term: TermId
    name: str


class EvidenceView(TermView):
    quote: str


class SignalView(DTO):
    category: CrisisCategory
    quote: str


class HelplineView(DTO):
    name: str
    phone: str
    note: str = ""


class PracticeSourceView(DTO):
    title: str
    url: str


class PracticeGuideView(DTO):
    steps: tuple[str, ...]
    limits: tuple[str, ...]
    sources: tuple[PracticeSourceView, ...]


class PracticeView(TermView):
    description: str
    guide: PracticeGuideView
    cautions: tuple[TermView, ...]


class RuleView(DTO):
    rule: RuleId
    explanation: str


class ReferralView(DTO):
    referral: Referral
    text: str


class ApproximationView(DTO):
    fact: FactKind
    confidence: float
    text: str


class CaseView(DTO):
    manifestations: tuple[EvidenceView, ...]
    stressors: tuple[EvidenceView, ...]
    unrecognized: tuple[str, ...]
    duration_weeks: int | None
    frequency: Frequency | None
    impact: ImpactDegree | None
    affected_domains: tuple[TermView, ...]
    self_harm: SelfHarmScreening | None
    sleep: ChangeDirection | None
    appetite: ChangeDirection | None
    energy: ChangeDirection | None
    substance_use: bool | None
    goal: str | None
    refused: tuple[FactKind, ...]


class SummaryView(DTO):
    level: UrgencyLevel | None
    phrase: str | None
    description: str
    specialist_request: str
    specialist: str
    crisis: bool
    referrals: tuple[ReferralView, ...]
    helplines: tuple[HelplineView, ...]
    signals: tuple[SignalView, ...]
    support_others: str | None
    practices: tuple[PracticeView, ...]
    clusters: tuple[TermView, ...]
    explanation: tuple[RuleView, ...]
    missing: tuple[FactKind, ...]
    approximations: tuple[ApproximationView, ...]
    case: CaseView
    disclaimer: str
