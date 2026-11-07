from collections.abc import Mapping
from typing import Annotated, NewType, Self

from pydantic import Field, field_validator, model_validator

from anamnesis.application.dto.base import DTO
from anamnesis.domain.enums.fact_kind import ESTIMATED_FACTS, FactKind


LinguisticTerm = NewType("LinguisticTerm", str)
"""Терм лингвистической переменной: `few_weeks`, `most_days`, `moderate`."""


class Estimate(DTO):
    """Оценка сведения по словам пользователя — договор извлечения и нормализации.

    Размытая оценка — степени термов: «пару недель» дают `few_weeks` со
    степенью 1. Точная — число в единицах переменной: «три недели» дают 3.

    Attributes:
        fact: Вид сведения из `ESTIMATED_FACTS`.
        terms: Степени термов из `(0, 1]`; пусто у точной оценки.
        value: Число; `None` у размытой оценки.
    """

    fact: FactKind
    terms: Mapping[LinguisticTerm, Annotated[float, Field(gt=0, le=1)]] = Field(
        default_factory=dict,
    )
    value: float | None = Field(default=None, ge=0)

    @property
    def is_exact(self) -> bool:
        """Оценка — число, а не размытые слова."""
        return self.value is not None

    @field_validator("fact")
    @classmethod
    def _validate_fact(cls, fact: FactKind) -> FactKind:
        if fact not in ESTIMATED_FACTS:
            raise ValueError(f"'{fact}' is not an estimated fact")
        return fact

    @model_validator(mode="after")
    def _validate_source(self) -> Self:
        if bool(self.terms) == (self.value is not None):
            raise ValueError("must have either terms or a value")
        return self
