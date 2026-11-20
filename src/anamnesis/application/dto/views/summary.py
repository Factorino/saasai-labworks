from anamnesis.application.dto.base import DTO
from anamnesis.application.interfaces.knowledge.knowledge_base import (
    Helpline,
    PracticeGuide,
    PracticeSource,
)
from anamnesis.domain.enums.change_direction import ChangeDirection
from anamnesis.domain.enums.crisis import CrisisCategory, SelfHarmScreening
from anamnesis.domain.enums.fact_kind import FactKind
from anamnesis.domain.enums.recommendation import Referral, UrgencyLevel
from anamnesis.domain.enums.scales import Frequency, ImpactDegree
from anamnesis.domain.types import RuleId, TermId
from anamnesis.domain.value_objects.crisis_signal import CrisisSignal


class TermView(DTO):
    """Понятие онтологии с названием на языке чата.

    Attributes:
        term: Представитель понятия.
        name: Название для человека.
    """

    term: TermId
    name: str


class EvidenceView(TermView):
    """Найденное понятие с цитатой-обоснованием.

    Attributes:
        quote: Фрагмент реплики пользователя; пуст, если сведения переданы без текста.
    """

    quote: str


class SignalView(DTO):
    """Находка кризисного детектора.

    Attributes:
        category: Что найдено.
        quote: Фрагмент реплики.
    """

    category: CrisisCategory
    quote: str

    @classmethod
    def from_domain(cls, signal: CrisisSignal) -> "SignalView":
        return cls(category=signal.category, quote=signal.quote)


class HelplineView(DTO):
    """Контакт службы помощи.

    Attributes:
        name: Название службы.
        phone: Номер телефона.
        note: Пояснение: часы работы, для кого служба.
    """

    name: str
    phone: str
    note: str = ""

    @classmethod
    def from_helpline(cls, helpline: Helpline) -> "HelplineView":
        return cls(name=helpline.name, phone=helpline.phone, note=helpline.note)


class PracticeSourceView(DTO):
    """Источник, на котором основана практика.

    Attributes:
        title: Название источника.
        url: Ссылка.
    """

    title: str
    url: str

    @classmethod
    def from_source(cls, source: PracticeSource) -> "PracticeSourceView":
        return cls(title=source.title, url=source.url)


class PracticeGuideView(DTO):
    """Документ практики самопомощи.

    Attributes:
        steps: Шаги выполнения.
        limits: Ограничения: когда практика не подходит.
        sources: Источники.
    """

    steps: tuple[str, ...]
    limits: tuple[str, ...]
    sources: tuple[PracticeSourceView, ...]

    @classmethod
    def from_guide(cls, guide: PracticeGuide) -> "PracticeGuideView":
        sources: tuple[PracticeSourceView, ...] = tuple(
            PracticeSourceView.from_source(source) for source in guide.sources
        )
        view: PracticeGuideView = cls(steps=guide.steps, limits=guide.limits, sources=sources)
        return view


class PracticeView(TermView):
    """Практика самопомощи в сводке.

    Attributes:
        description: Описание практики.
        guide: Как её выполнять.
        cautions: Понятия случая, из-за которых практику показывают с предупреждением.
    """

    description: str
    guide: PracticeGuideView
    cautions: tuple[TermView, ...]


class RuleView(DTO):
    """Сработавшее правило с объяснением.

    Attributes:
        rule: Правило онтологии (`R12`).
        explanation: Объяснение для человека.
    """

    rule: RuleId
    explanation: str


class ReferralView(DTO):
    """Направление за помощью.

    Attributes:
        referral: Куда обратиться.
        text: Совет на языке чата.
    """

    referral: Referral
    text: str


class ApproximationView(DTO):
    """Сведение, оценённое приблизительно, по размытым словам.

    Attributes:
        fact: Какое сведение.
        confidence: Уверенность в значении, из `(0, 1]`.
        text: Отметка о приблизительности для человека.
    """

    fact: FactKind
    confidence: float
    text: str


class CaseView(DTO):
    """Собранные сведения о случае.

    Неизвестное сведение — `None` или пустой кортеж.

    Attributes:
        manifestations: Найденные проявления с цитатами.
        stressors: Найденные стрессоры с цитатами.
        unrecognized: Жалобы вне понятий онтологии.
        duration_weeks: Длительность в неделях.
        frequency: Частота.
        impact: Влияние на жизнь.
        affected_domains: Затронутые сферы жизни.
        self_harm: Скрининг самоповреждения.
        sleep: Изменение сна.
        appetite: Изменение аппетита.
        energy: Изменение энергии.
        substance_use: Употребляет ли человек вещества, чтобы стало легче.
        goal: Чего человек хочет от встречи со специалистом.
        refused: От каких вопросов человек отказался.
    """

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
    """Итоговая сводка для человека и для специалиста.

    Attributes:
        level: Уровень срочности; `None` — «недостаточно данных».
        phrase: Формулировка уровня; `None`, если самопомощь не советуется при L0.
        description: Состояние простыми словами: от модели или шаблон.
        specialist_request: Запрос к специалисту от первого лица: от модели или шаблон.
        specialist: Подсказка, к какому специалисту обратиться.
        crisis: Кризисный сценарий.
        referrals: Направления за помощью в порядке показа.
        helplines: Контакты помощи; есть при срочном направлении.
        signals: Находки кризисного детектора за диалог.
        support_others: Совет, как поддержать близкого; есть, если человек тревожится за
            другого.
        practices: Практики самопомощи в порядке показа.
        clusters: Кластеры состояний — для объяснения.
        explanation: Сработавшие правила с объяснениями.
        missing: Обязательные сведения, которых не хватило.
        approximations: Сведения, оценённые по размытым словам.
        case: Собранные сведения о случае.
        disclaimer: Предупреждение, что сводка — не диагноз.
    """

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
