from collections.abc import Collection
from datetime import date
from typing import Any, Literal, cast

from pydantic import Field, create_model

from anamnesis.application.dto.base import DTO
from anamnesis.application.dto.estimate import LinguisticTerm
from anamnesis.application.interfaces.llm.language_model import ModelData
from anamnesis.domain.enums.fact_kind import FactKind
from anamnesis.domain.types import TermId


class CandidateData(DTO):
    """Понятие, которое словарь уже нашёл в реплике: подсказка для модели.

    Attributes:
        concept: Представитель понятия.
        quote: Фрагмент реплики, по которому оно найдено.
    """

    concept: TermId
    quote: str


class ExtractionData(ModelData):
    """Данные задачи извлечения сведений из одной реплики.

    Attributes:
        text: Реплика пользователя.
        question: На какой вопрос это ответ; `None` — свободный рассказ.
        today: Текущая дата: для выражений вроде «с сентября».
        candidates: Понятия, найденные словарём.
    """

    text: str
    question: FactKind | None
    today: date
    candidates: tuple[CandidateData, ...]


class FoundConcept(DTO):
    """Понятие онтологии, найденное языковой моделью, и цитата-обоснование.

    Attributes:
        term: Представитель понятия (`Anxiety_`).
        quote: Точный фрагмент реплики, в котором видно понятие.
    """

    term: TermId
    quote: str = Field(description="Exact fragment of the user's text that shows the concept")


class ExtractionReply(DTO):
    """Ответ языковой модели при извлечении сведений.

    Поля задают форму JSON-схемы; допустимые понятия и термы подставляет
    `reply_model`, поэтому модель не может вернуть значение вне онтологии.
    """

    manifestations: tuple[FoundConcept, ...] = Field(
        description="Concepts of what the user feels, thinks, does or notices in the body",
    )
    stressors: tuple[FoundConcept, ...] = Field(
        description="Concepts of life circumstances that weigh on the user",
    )
    other: tuple[str, ...] = Field(
        description="Exact fragments with complaints that match no listed concept",
    )
    duration: LinguisticTerm | None = Field(
        description="How long it has lasted, only if the user says so",
    )
    frequency: LinguisticTerm | None = Field(
        description="How often it happens, only if the user says so",
    )
    impact: LinguisticTerm | None = Field(
        description="How much it interferes with life, only if the user says so",
    )
    goal: str | None = Field(
        description="Exact fragment saying what the user wants from a specialist, only if stated",
    )


def reply_model(
    *,
    manifestations: Collection[TermId],
    stressors: Collection[TermId],
    durations: Collection[LinguisticTerm],
    frequencies: Collection[LinguisticTerm],
    impacts: Collection[LinguisticTerm],
) -> type[ExtractionReply]:
    """Подкласс `ExtractionReply`, в схеме которого понятия и термы — перечисления."""
    base: Any = ExtractionReply.model_fields
    return create_model(
        "ExtractionReply",
        __base__=ExtractionReply,
        manifestations=(_concepts("Manifestation", manifestations), base["manifestations"]),
        stressors=(_concepts("Stressor", stressors), base["stressors"]),
        duration=(_optional_one_of(durations), base["duration"]),
        frequency=(_optional_one_of(frequencies), base["frequency"]),
        impact=(_optional_one_of(impacts), base["impact"]),
    )


def _concepts(name: str, terms: Collection[TermId]) -> Any:
    """Тип `tuple[<name>, ...]`, где `term` — одно из понятий."""
    item: type[FoundConcept] = create_model(
        name,
        __base__=FoundConcept,
        term=(_one_of(terms), Field(description="Concept identifier from the list")),
    )
    return cast("Any", tuple)[item, ...]


def _one_of(values: Collection[str]) -> Any:
    """`Literal` из значений, построенный во время выполнения."""
    return cast("Any", Literal)[tuple(sorted(values))]


def _optional_one_of(values: Collection[str]) -> Any:
    """`Literal` из значений или `None`.

    Объединение собирается здесь, а не на месте вызова: иначе pyright видит в
    `Literal[...] | None` значение `UnionType`, а `create_model` ждёт `TypeForm`.
    """
    return _one_of(values) | None
