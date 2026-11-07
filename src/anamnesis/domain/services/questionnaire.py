from collections.abc import Collection, Mapping
from types import MappingProxyType
from typing import Final

from anamnesis.domain.enums.change_direction import ChangeDirection
from anamnesis.domain.enums.fact_kind import FactKind
from anamnesis.domain.enums.frequency import Frequency
from anamnesis.domain.enums.impact_degree import ImpactDegree
from anamnesis.domain.enums.self_harm_screening import SelfHarmScreening
from anamnesis.domain.errors.common import ValidationError
from anamnesis.domain.types import OptionCode, TermId
from anamnesis.domain.value_objects.case_facts import CaseFacts
from anamnesis.domain.value_objects.duration import Duration
from anamnesis.domain.value_objects.question import REFUSE_OPTION_CODE, Answer, Question


type _Choices = Mapping[OptionCode, CaseFacts]
"""Варианты ответа на вопрос: код варианта и сведения, которые он даёт."""


def _choices(**items: CaseFacts) -> _Choices:
    """Таблица вариантов, имена аргументов становятся кодами вариантов."""
    return MappingProxyType({OptionCode(code): facts for code, facts in items.items()})


_DURATION: Final[_Choices] = _choices(
    less_than_week=CaseFacts(duration=Duration(weeks=0)),
    about_week=CaseFacts(duration=Duration(weeks=1)),
    two_three_weeks=CaseFacts(duration=Duration(weeks=2)),
    about_month=CaseFacts(duration=Duration(weeks=4)),
    few_months=CaseFacts(duration=Duration(weeks=12)),
    half_year_or_more=CaseFacts(duration=Duration(weeks=26)),
)
"""Длительность записывается по нижней границе интервала."""

_FREQUENCY: Final[_Choices] = _choices(
    rarely=CaseFacts(frequency=Frequency.RARELY),
    several_times_a_week=CaseFacts(frequency=Frequency.SEVERAL_TIMES_A_WEEK),
    most_days=CaseFacts(frequency=Frequency.MOST_DAYS),
    constantly=CaseFacts(frequency=Frequency.CONSTANTLY),
)
"""Частота — шкала свойства `frequency` онтологии."""

_IMPACT: Final[_Choices] = _choices(
    none=CaseFacts(impact=ImpactDegree.NONE),
    mild=CaseFacts(impact=ImpactDegree.MILD),
    moderate=CaseFacts(impact=ImpactDegree.MODERATE),
    severe=CaseFacts(impact=ImpactDegree.SEVERE),
)
"""Влияние на жизнь — шкала свойства `impactDegree` онтологии."""

_AFFECTED_DOMAINS: Final[_Choices] = _choices(
    work_and_study=CaseFacts(affected_domains=frozenset({TermId("WorkAndStudy_")})),
    relationships=CaseFacts(affected_domains=frozenset({TermId("Relationships_")})),
    daily_life=CaseFacts(affected_domains=frozenset({TermId("DailyLife_")})),
    leisure_and_community=CaseFacts(
        affected_domains=frozenset({TermId("LeisureAndCommunity_")}),
    ),
)
"""Сферы жизни — представители четырёх подклассов `LifeDomain` онтологии."""

_SELF_HARM: Final[_Choices] = _choices(
    none=CaseFacts(self_harm=SelfHarmScreening.NONE),
    passive=CaseFacts(self_harm=SelfHarmScreening.PASSIVE),
    active=CaseFacts(self_harm=SelfHarmScreening.ACTIVE),
    plan=CaseFacts(self_harm=SelfHarmScreening.PLAN),
)
"""Скрининг самоповреждения, `active` и `plan` переводят чат в кризис."""

_SLEEP: Final[_Choices] = _choices(
    unchanged=CaseFacts(sleep=ChangeDirection.UNCHANGED),
    decreased=CaseFacts(sleep=ChangeDirection.DECREASED),
    increased=CaseFacts(sleep=ChangeDirection.INCREASED),
)
"""Изменение сна, в онтологию не передаётся."""

_ENERGY: Final[_Choices] = _choices(
    unchanged=CaseFacts(energy=ChangeDirection.UNCHANGED),
    decreased=CaseFacts(energy=ChangeDirection.DECREASED),
    increased=CaseFacts(energy=ChangeDirection.INCREASED),
)
"""Изменение энергии, в онтологию не передаётся."""

_APPETITE: Final[_Choices] = _choices(
    unchanged=CaseFacts(appetite=ChangeDirection.UNCHANGED),
    decreased=CaseFacts(appetite=ChangeDirection.DECREASED),
    increased=CaseFacts(appetite=ChangeDirection.INCREASED),
)
"""Изменение аппетита, в онтологию не передаётся."""

_SUBSTANCE_USE: Final[_Choices] = _choices(
    no=CaseFacts(substance_use=False),
    yes=CaseFacts(substance_use=True),
)
"""Употребляет ли человек вещества."""

_CHOICES: Final[Mapping[FactKind, _Choices]] = MappingProxyType(
    {
        FactKind.DURATION: _DURATION,
        FactKind.FREQUENCY: _FREQUENCY,
        FactKind.IMPACT: _IMPACT,
        FactKind.AFFECTED_DOMAINS: _AFFECTED_DOMAINS,
        FactKind.SELF_HARM: _SELF_HARM,
        FactKind.SLEEP: _SLEEP,
        FactKind.ENERGY: _ENERGY,
        FactKind.APPETITE: _APPETITE,
        FactKind.SUBSTANCE_USE: _SUBSTANCE_USE,
    },
)
"""Варианты по видам сведений. у вопросов со свободным текстом вариантов нет."""

_FREE_TEXT: Final[frozenset[FactKind]] = frozenset(
    {
        FactKind.MANIFESTATIONS,
        FactKind.DURATION,
        FactKind.FREQUENCY,
        FactKind.IMPACT,
        FactKind.GOAL,
    },
)
"""Вопросы, на которые можно ответить своими словами; у части из них есть и варианты."""

_MULTIPLE: Final[frozenset[FactKind]] = frozenset({FactKind.AFFECTED_DOMAINS})
"""Вопросы, в которых можно выбрать несколько вариантов."""


def _build_question(kind: FactKind, *, follow_up: bool = False) -> Question:
    """Вопрос о сведении: его варианты и в конце вариант отказа."""
    choices: _Choices = _CHOICES.get(kind, MappingProxyType({}))
    return Question(
        fact=kind,
        options=(*choices, REFUSE_OPTION_CODE),
        multiple=kind in _MULTIPLE,
        free_text=kind in _FREE_TEXT,
        follow_up=follow_up,
    )


class Questionnaire:
    """Шаблонные уточняющие вопросы и разбор ответов на них.

    Сервис без состояния: какие вопросы уже заданы, хранит чат. Тексты
    вопросов лежат в файлах локализации, здесь только коды.

    Attributes:
        ORDER: Порядок вопросов: сначала обязательные сведения, затем желательные.
        DEFAULT_QUESTION_LIMIT: Сколько вопросов задавать по умолчанию.
    """

    ORDER: Final[tuple[FactKind, ...]] = (
        FactKind.MANIFESTATIONS,
        FactKind.DURATION,
        FactKind.FREQUENCY,
        FactKind.IMPACT,
        FactKind.AFFECTED_DOMAINS,
        FactKind.SELF_HARM,
        FactKind.SLEEP,
        FactKind.ENERGY,
        FactKind.APPETITE,
        FactKind.SUBSTANCE_USE,
        FactKind.GOAL,
    )

    DEFAULT_QUESTION_LIMIT: Final[int] = 8

    def __init__(self, question_limit: int = DEFAULT_QUESTION_LIMIT) -> None:
        self._validate_question_limit(question_limit)
        self._question_limit: int = question_limit
        self._questions: Mapping[FactKind, Question] = MappingProxyType(
            {kind: _build_question(kind) for kind in self.ORDER},
        )
        self._self_harm_follow_up: Question = _build_question(
            FactKind.SELF_HARM,
            follow_up=True,
        )

    @property
    def question_limit(self) -> int:
        """Сколько вопросов задать."""
        return self._question_limit

    @property
    def self_harm_follow_up(self) -> Question:
        """Повторный вопрос о самоповреждении.

        Задаётся один раз, если правила направили к службам помощи
        (`CrisisHelpline_`), а на основной вопрос пользователь не ответил.
        """
        return self._self_harm_follow_up

    def question(self, kind: FactKind) -> Question:
        """Вопрос о сведении указанного вида."""
        return self._questions[kind]

    def next_question(self, facts: CaseFacts, asked: Collection[FactKind]) -> Question | None:
        """Следующий вопрос по порядку `ORDER`.

        Пропускаются вопросы, которые уже задавали, и сведения, которые
        известны или от которых отказались. Про сферы жизни спрашивают только
        при влиянии ≥ 1.

        Args:
            facts: Что известно о случае.
            asked: Какие вопросы уже заданы.

        Returns:
            Вопрос или `None`, если спрашивать больше нечего.
        """
        within_limit: bool = len(asked) < self._question_limit
        for kind in self.ORDER:
            if kind in asked or facts.is_settled(kind) or not self._applies(kind, facts):
                continue
            if within_limit or kind is FactKind.SELF_HARM:
                return self._questions[kind]
        return None

    def apply(
        self,
        facts: CaseFacts,
        question: Question,
        answer: Answer,
        extracted: CaseFacts | None = None,
    ) -> CaseFacts:
        """Добавляет к сведениям ответ на вопрос.

        Отказ отмечается в `refused`. Текст становится целью обращения,
        добавляется к проявлениям или даёт сведения через `extracted`. Каждый
        выбранный вариант даёт свою часть сведений.

        Args:
            facts: Что известно о случае.
            question: Вопрос, на который ответили.
            answer: Ответ пользователя.
            extracted: Сведения, извлечённые из текста ответа вне домена; для
                вопроса о проявлениях это единственный источник терминов, для
                длительности, частоты и влияния — оценка по словам.

        Returns:
            Новые сведения о случае.

        Raises:
            ValidationError: Ответ не подходит к вопросу.
        """
        self._validate_answer(question, answer)
        found: CaseFacts = extracted if extracted is not None else CaseFacts()
        if answer.is_refusal:
            return facts.merge(found).refuse(question.fact)
        if answer.text is not None:
            return self._apply_text(facts, question.fact, answer.text, found)
        return facts.merge(found).merge(self._apply_choice(question.fact, answer.option_codes))

    @staticmethod
    def _applies(kind: FactKind, facts: CaseFacts) -> bool:
        """Уместен ли вопрос: о сферах жизни — только если проявления мешают жить."""
        if kind is FactKind.AFFECTED_DOMAINS:
            return facts.impact is not None and facts.impact >= ImpactDegree.MILD
        return True

    @staticmethod
    def _validate_question_limit(question_limit: int) -> None:
        if question_limit < 0:
            raise ValidationError(field="Question limit", reason="must not be negative")

    @classmethod
    def _validate_answer(cls, question: Question, answer: Answer) -> None:
        """Проверяет ответ по виду: отказ, свой текст или выбор вариантов."""
        if answer.is_refusal:
            cls._validate_refusal(question, answer)
        elif answer.text is not None:
            cls._validate_text_answer(question, answer)
        else:
            cls._validate_choice(question, answer)

    @staticmethod
    def _validate_refusal(question: Question, answer: Answer) -> None:
        """Отказ нельзя совмещать с другим вариантом или текстом."""
        if len(answer.option_codes) > 1 or answer.text is not None:
            raise ValidationError(
                field=question.fact,
                reason="a refusal cannot be combined with another answer",
            )

    @staticmethod
    def _validate_text_answer(question: Question, answer: Answer) -> None:
        """Своими словами — только где можно и без вариантов вместе с текстом."""
        if not question.free_text:
            raise ValidationError(field=question.fact, reason="expects one of the options")
        if answer.option_codes:
            raise ValidationError(
                field=question.fact,
                reason="expects either an option or a text, not both",
            )

    @staticmethod
    def _validate_choice(question: Question, answer: Answer) -> None:
        """Нужен хотя бы один известный вариант; несколько — только где можно."""
        codes: tuple[OptionCode, ...] = answer.option_codes
        if question.fact not in _CHOICES:
            raise ValidationError(field=question.fact, reason="expects a text answer")
        if not codes:
            raise ValidationError(field=question.fact, reason="expects one of the options")
        if len(codes) > 1 and not question.multiple:
            raise ValidationError(field=question.fact, reason="expects a single option")
        choices: _Choices = _CHOICES[question.fact]
        for code in codes:
            if code not in choices:
                raise ValidationError(field=question.fact, reason=f"unknown option '{code}'")

    @staticmethod
    def _apply_text(facts: CaseFacts, kind: FactKind, text: str, found: CaseFacts) -> CaseFacts:
        """Текст становится целью, добавляется к проявлениям или даёт оценку сведения."""
        if kind is FactKind.GOAL:
            return facts.merge(found).merge(CaseFacts(goal=text))
        if kind is FactKind.MANIFESTATIONS:
            return facts.absorb(text, found)
        return facts.merge(found)

    @staticmethod
    def _apply_choice(kind: FactKind, codes: tuple[OptionCode, ...]) -> CaseFacts:
        """Сведения из выбранных вариантов."""
        choices: _Choices = _CHOICES[kind]
        result: CaseFacts = CaseFacts()
        for code in codes:
            result = result.merge(choices[code])
        return result
