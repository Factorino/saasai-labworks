from collections.abc import Mapping
from pathlib import Path
from types import MappingProxyType
from typing import ClassVar

from pydantic import BaseModel, ConfigDict
import yaml

from anamnesis.application.dto.estimate import LinguisticTerm
from anamnesis.domain.enums.fact_kind import ESTIMATED_FACTS, FactKind
from anamnesis.infrastructure.fuzzy.linguistic_variable import LinguisticVariable
from anamnesis.infrastructure.fuzzy.membership import Trapezoid


class _Variable(BaseModel):
    """Переменная в файле: универсум `[low, high]` и трапеции `[a, b, c, d]`."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")

    universe: tuple[float, float]
    terms: Mapping[LinguisticTerm, tuple[float, float, float, float]]


def load_linguistic_variables(path: Path) -> Mapping[FactKind, LinguisticVariable]:
    """Лингвистические переменные из файла знаний.

    Raises:
        ValueError: Переменных не хватает, есть лишние или параметры неверны.
    """
    with path.open(encoding="utf-8") as file:
        data: Mapping[str, object] = yaml.safe_load(file)
    variables: dict[FactKind, LinguisticVariable] = {}
    for key, raw in data.items():
        fact: FactKind = FactKind(key)
        parsed: _Variable = _Variable.model_validate(raw)
        variables[fact] = LinguisticVariable(
            low=parsed.universe[0],
            high=parsed.universe[1],
            terms={
                term: Trapezoid(a=a, b=b, c=c, d=d) for term, (a, b, c, d) in parsed.terms.items()
            },
        )
    _validate_facts(frozenset(variables))
    return MappingProxyType(variables)


def _validate_facts(facts: frozenset[FactKind]) -> None:
    if facts != ESTIMATED_FACTS:
        raise ValueError(
            f"Linguistic variables must cover exactly {sorted(ESTIMATED_FACTS)}, "
            f"got {sorted(facts)}",
        )
