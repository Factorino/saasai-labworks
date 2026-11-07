from collections.abc import Mapping
from enum import IntEnum
import math
from types import MappingProxyType
from typing import Final, override

from anamnesis.application.dto.estimate import Estimate, LinguisticTerm
from anamnesis.application.interfaces.extraction.fact_normalizer import IFactNormalizer
from anamnesis.domain.enums.fact_kind import FactKind
from anamnesis.domain.enums.frequency import Frequency
from anamnesis.domain.enums.impact_degree import ImpactDegree
from anamnesis.domain.value_objects.case_facts import CaseFacts
from anamnesis.domain.value_objects.duration import Duration
from anamnesis.infrastructure.fuzzy.linguistic_variable import LinguisticVariable


_PRECISION: Final[int] = 2
"""Знаков после запятой в уверенности: центр тяжести считается численно."""


class FuzzyFactNormalizer(IFactNormalizer):
    """Нормализация по лингвистическим переменным с дефаззификацией центром тяжести.

    Длительность берётся по нижней целой границе в неделях. Частота и
    влияние — термом с наибольшей степенью принадлежности, поэтому их термы
    обязаны совпадать с кодами шкал. Эта степень сохраняется как
    уверенность. Точная оценка (число) отметки о приблизительности не
    получает.
    """

    def __init__(self, variables: Mapping[FactKind, LinguisticVariable]) -> None:
        self._variables: Mapping[FactKind, LinguisticVariable] = variables
        self._frequencies: Mapping[LinguisticTerm, Frequency] = _scale(
            variables[FactKind.FREQUENCY], Frequency
        )
        self._impacts: Mapping[LinguisticTerm, ImpactDegree] = _scale(
            variables[FactKind.IMPACT], ImpactDegree
        )

    @override
    def normalize(self, estimate: Estimate) -> CaseFacts:
        variable: LinguisticVariable = self._variables[estimate.fact]
        crisp: float = (
            estimate.value if estimate.value is not None else variable.defuzzify(estimate.terms)
        )
        term, degree = variable.classify(crisp)
        confidence: Mapping[FactKind, float] = (
            MappingProxyType({})
            if estimate.is_exact
            else MappingProxyType({estimate.fact: round(degree, _PRECISION)})
        )
        match estimate.fact:
            case FactKind.DURATION:
                weeks: int = min(math.floor(crisp), Duration.MAX_WEEKS)
                return CaseFacts(duration=Duration(weeks=weeks), confidence=confidence)
            case FactKind.FREQUENCY:
                return CaseFacts(frequency=self._frequencies[term], confidence=confidence)
            case _:
                return CaseFacts(impact=self._impacts[term], confidence=confidence)


def _scale[ScaleT: IntEnum](
    variable: LinguisticVariable,
    scale: type[ScaleT],
) -> Mapping[LinguisticTerm, ScaleT]:
    """Соответствие термов кодам шкалы; термы и коды должны совпадать.

    Raises:
        ValueError: Набор термов отличается от кодов шкалы.
    """
    codes: Mapping[LinguisticTerm, ScaleT] = MappingProxyType(
        {LinguisticTerm(member.name.lower()): member for member in scale},
    )
    if set(variable.terms) != set(codes):
        raise ValueError(f"Terms of {scale.__name__} must be {sorted(codes)}")
    return codes
