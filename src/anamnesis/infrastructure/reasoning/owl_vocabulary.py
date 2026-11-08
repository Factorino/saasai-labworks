from collections.abc import Iterable
from pathlib import Path
from types import MappingProxyType
from typing import Any, Final, override

from owlready2 import World

from anamnesis.application.interfaces.knowledge.vocabulary import IOntologyVocabulary, Vocabulary
from anamnesis.domain.types import TermId


_REPRESENTATIVE_SUFFIX: Final[str] = "_"
"""Индивид-представитель понятия называется по классу с `_` на конце."""

_RESERVED_CLASSES: Final[tuple[str, ...]] = ("RiskMarker", "SelfHarmThoughts")
"""Классы, понятия которых утверждает только детерминированный контур."""


class OwlOntologyVocabulary(IOntologyVocabulary):
    """Понятия проявлений и стрессоров, прочитанные из онтологии один раз при запуске."""

    def __init__(self, *, ontology_path: Path) -> None:
        world: Any = World()
        try:
            onto: Any = world.get_ontology(ontology_path.resolve().as_uri()).load()
            self._vocabulary: Vocabulary = Vocabulary(
                manifestations=_representatives(onto.Manifestation.instances()),
                stressors=_representatives(onto.Stressor.instances()),
                reserved=frozenset().union(
                    *(_representatives(onto[name].instances()) for name in _RESERVED_CLASSES),
                ),
                concepts=MappingProxyType(
                    {
                        TermId(individual.name): concept
                        for kind in (onto.Manifestation, onto.Stressor)
                        for individual in kind.instances()
                        if (concept := _concept(individual)) is not None
                    },
                ),
            )
        finally:
            world.close()

    @override
    def vocabulary(self) -> Vocabulary:
        return self._vocabulary


def _representatives(individuals: Iterable[Any]) -> frozenset[TermId]:
    return frozenset(
        TermId(individual.name)
        for individual in individuals
        if individual.name.endswith(_REPRESENTATIVE_SUFFIX)
    )


def _concept(individual: Any) -> TermId | None:
    """Представитель класса, к которому относится термин."""
    for cls in individual.is_a:
        name: str = f"{cls.name}{_REPRESENTATIVE_SUFFIX}"
        if cls.namespace.ontology[name] is not None:
            return TermId(name)
    return None
