from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import ClassVar

from anamnesis.application.dto.estimate import LinguisticTerm
from anamnesis.infrastructure.fuzzy.membership import Trapezoid


@dataclass(frozen=True, slots=True)
class LinguisticVariable:
    """Лингвистическая переменная: универсум и термы с функциями принадлежности.

    Attributes:
        low: Нижняя граница универсума.
        high: Верхняя граница универсума.
        terms: Термы по возрастанию значения и их функции принадлежности.
    """

    STEPS: ClassVar[int] = 1000
    """На сколько отрезков делится универсум при вычислении центра тяжести."""

    low: float
    high: float
    terms: Mapping[LinguisticTerm, Trapezoid]

    def __post_init__(self) -> None:
        self._normalize()
        self._validate()

    def clamp(self, x: float) -> float:
        """Значение, приведённое к границам универсума."""
        return min(max(x, self.low), self.high)

    def fuzzify(self, x: float) -> Mapping[LinguisticTerm, float]:
        """Степени принадлежности значения каждому терму."""
        return MappingProxyType({term: mf.degree(x) for term, mf in self.terms.items()})

    def classify(self, x: float) -> tuple[LinguisticTerm, float]:
        """Терм с наибольшей степенью принадлежности значения и сама степень.

        При равных степенях выбирается терм, объявленный раньше, то есть
        меньший: оценка не завышается.
        """
        degrees: Mapping[LinguisticTerm, float] = self.fuzzify(self.clamp(x))
        best: LinguisticTerm = max(degrees, key=lambda term: degrees[term])
        return best, degrees[best]

    def defuzzify(self, weights: Mapping[LinguisticTerm, float]) -> float:
        """Чёткое значение нечёткого множества методом центра тяжести.

        Множество строится по Мамдани: функция каждого терма срезается на его
        степени (минимум), срезы объединяются (максимум).

        Args:
            weights: Степени термов из `(0, 1]`.

        Returns:
            Абсцисса центра тяжести фигуры под функцией множества.

        Raises:
            ValueError: Степеней нет или терм неизвестен.
        """
        self._validate_weights(weights)
        step: float = (self.high - self.low) / self.STEPS
        area: float = 0.0
        moment: float = 0.0
        for index in range(self.STEPS + 1):
            x: float = self.low + index * step
            mu: float = max(
                min(weight, self.terms[term].degree(x)) for term, weight in weights.items()
            )
            area += mu
            moment += mu * x
        return moment / area

    def _normalize(self) -> None:
        object.__setattr__(self, "terms", MappingProxyType(dict(self.terms)))

    def _validate(self) -> None:
        if self.low >= self.high:
            raise ValueError("Universe low bound must be below the high bound")
        if not self.terms:
            raise ValueError("Linguistic variable must have terms")
        for term, mf in self.terms.items():
            if mf.a < self.low or mf.d > self.high:
                raise ValueError(f"Term '{term}' leaves the universe")

    def _validate_weights(self, weights: Mapping[LinguisticTerm, float]) -> None:
        if not weights:
            raise ValueError("Weights must not be empty")
        unknown: set[LinguisticTerm] = set(weights) - set(self.terms)
        if unknown:
            raise ValueError(f"Unknown terms {sorted(unknown)}")
