from collections.abc import Mapping
from pathlib import Path
from types import MappingProxyType

from anamnesis.application.dto.estimate import LinguisticTerm
from anamnesis.domain.enums.fact_kind import ESTIMATED_FACTS, FactKind
from anamnesis.infrastructure.filesystem.yaml_reader import YamlFile, read_yaml
from anamnesis.infrastructure.fuzzy.linguistic_variable import LinguisticVariable
from anamnesis.infrastructure.fuzzy.membership import Trapezoid


type LinguisticVariables = Mapping[FactKind, LinguisticVariable]
"""Лингвистические переменные оцениваемых сведений."""


class VariableEntry(YamlFile):
    """Переменная в файле: универсум `[low, high]` и трапеции `[a, b, c, d]` термов.

    Attributes:
        universe: Границы универсума.
        terms: Термы по возрастанию значения и их трапеции.
    """

    universe: tuple[float, float]
    terms: Mapping[LinguisticTerm, tuple[float, float, float, float]]

    def to_variable(self) -> LinguisticVariable:
        """Лингвистическая переменная по записи файла."""
        low, high = self.universe
        variable: LinguisticVariable = LinguisticVariable(
            low=low,
            high=high,
            terms={
                term: Trapezoid(a=a, b=b, c=c, d=d) for term, (a, b, c, d) in self.terms.items()
            },
        )
        return variable


class LinguisticVariablesFile(YamlFile):
    """`knowledge/linguistic_variables.yaml`: переменные длительности, частоты и влияния."""

    duration: VariableEntry
    frequency: VariableEntry
    impact: VariableEntry


def load_linguistic_variables(path: Path) -> LinguisticVariables:
    document: LinguisticVariablesFile = read_yaml(path, LinguisticVariablesFile)
    variables: LinguisticVariables = MappingProxyType(
        {
            FactKind.DURATION: document.duration.to_variable(),
            FactKind.FREQUENCY: document.frequency.to_variable(),
            FactKind.IMPACT: document.impact.to_variable(),
        },
    )
    if frozenset(variables) != ESTIMATED_FACTS:
        raise ValueError(f"Linguistic variables must cover exactly {sorted(ESTIMATED_FACTS)}")
    return variables
