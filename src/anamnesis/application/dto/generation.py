from pydantic import Field

from anamnesis.application.dto.base import DTO
from anamnesis.application.dto.views.summary import (
    CaseView,
    EvidenceView,
    PracticeView,
    SummaryView,
)
from anamnesis.application.interfaces.llm.language_model import ModelData
from anamnesis.domain.enums.change_direction import ChangeDirection
from anamnesis.domain.enums.chat import MessageRole
from anamnesis.domain.enums.fact_kind import FactKind
from anamnesis.domain.types import LanguageCode
from anamnesis.domain.value_objects.message import Message


class ConceptData(DTO):
    """Понятие, найденное в рассказе, для модели.

    Attributes:
        name: Название понятия на языке чата.
        quote: Фрагмент реплики пользователя.
    """

    name: str
    quote: str

    @classmethod
    def from_evidence(cls, evidence: EvidenceView) -> "ConceptData":
        return cls(name=evidence.name, quote=evidence.quote)


class PracticeData(DTO):
    """Документ подобранной практики: как её выполнять и когда нельзя.

    Attributes:
        name: Название практики.
        description: Описание.
        steps: Шаги выполнения.
        limits: Ограничения.
    """

    name: str
    description: str
    steps: tuple[str, ...]
    limits: tuple[str, ...]

    @classmethod
    def from_practice(cls, practice: PracticeView) -> "PracticeData":
        return cls(
            name=practice.name,
            description=practice.description,
            steps=practice.guide.steps,
            limits=practice.guide.limits,
        )


class HistoryData(DTO):
    """Реплика истории диалога для модели.

    Attributes:
        role: Автор реплики.
        text: Текст.
    """

    role: MessageRole
    text: str

    @classmethod
    def from_domain(cls, message: Message) -> "HistoryData":
        return cls(role=message.role, text=message.text)


class SummaryData(ModelData):
    """Результаты вывода и сведения для модели: только то, что описывает состояние.

    Данные задачи текста сводки и часть данных ответа на реплику.

    Attributes:
        language: Язык, на котором писать.
        urgency: Формулировка уровня; `None` — уровень не упоминать.
        reasons: Объяснения сработавших правил.
        manifestations: Проявления с цитатами.
        stressors: Стрессоры с цитатами.
        other: Жалобы вне понятий онтологии.
        duration_weeks: Длительность в неделях.
        frequency: Частота: имя члена `Frequency` в нижнем регистре.
        impact: Влияние на жизнь: имя члена `ImpactDegree` в нижнем регистре.
        affected_domains: Названия затронутых сфер.
        sleep: Изменение сна.
        appetite: Изменение аппетита.
        energy: Изменение энергии.
        goal: Чего человек хочет от встречи со специалистом.
        approximate: Сведения, оценённые по размытым словам.
        not_reported: Обязательные сведения, которых не хватило.
    """

    language: LanguageCode

    urgency: str | None
    reasons: tuple[str, ...]

    manifestations: tuple[ConceptData, ...]
    stressors: tuple[ConceptData, ...]
    other: tuple[str, ...]

    duration_weeks: int | None
    frequency: str | None
    impact: str | None
    affected_domains: tuple[str, ...]

    sleep: ChangeDirection | None
    appetite: ChangeDirection | None
    energy: ChangeDirection | None

    goal: str | None

    approximate: tuple[FactKind, ...]
    not_reported: tuple[FactKind, ...]

    @classmethod
    def from_summary(cls, language: LanguageCode, summary: SummaryView) -> "SummaryData":
        case: CaseView = summary.case

        data: SummaryData = cls(
            language=language,
            urgency=summary.phrase,
            reasons=tuple(rule.explanation for rule in summary.explanation),
            manifestations=tuple(ConceptData.from_evidence(item) for item in case.manifestations),
            stressors=tuple(ConceptData.from_evidence(item) for item in case.stressors),
            other=case.unrecognized,
            duration_weeks=case.duration_weeks,
            frequency=case.frequency.name.lower() if case.frequency is not None else None,
            impact=case.impact.name.lower() if case.impact is not None else None,
            affected_domains=tuple(item.name for item in case.affected_domains),
            sleep=case.sleep,
            appetite=case.appetite,
            energy=case.energy,
            goal=case.goal,
            approximate=tuple(item.fact for item in summary.approximations),
            not_reported=summary.missing,
        )
        return data


class AnswerData(ModelData):
    """Данные задачи ответа на реплику после сводки.

    Attributes:
        language: Язык, на котором писать.
        summary: Сводка.
        practices: Подобранные практики.
        history: Предыдущие реплики.
        message: Реплика, на которую нужно ответить.
    """

    language: LanguageCode
    summary: SummaryData
    practices: tuple[PracticeData, ...]
    history: tuple[HistoryData, ...]
    message: str


class NarrativeReply(DTO):
    """Ответ языковой модели с текстом сводки.

    Attributes:
        description: Состояние человека простыми тёплыми словами, три-пять предложений.
        request: Что человек может сказать специалисту, от первого лица.
    """

    description: str = Field(
        min_length=1,
        description="The person's state in plain, warm words, three to five sentences",
    )
    request: str = Field(
        min_length=1,
        description="What the person can say to a specialist, in the first person",
    )


class AnswerReply(DTO):
    """Ответ языковой модели на свободную реплику после сводки.

    Attributes:
        text: Текст ответа.
    """

    text: str = Field(min_length=1, description="The answer to the person's message")
