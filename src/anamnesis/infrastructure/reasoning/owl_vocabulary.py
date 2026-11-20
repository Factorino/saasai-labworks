from collections.abc import Mapping
from pathlib import Path
from types import MappingProxyType
from typing import Any, Final, override

from anamnesis.application.interfaces.knowledge.vocabulary import IOntologyVocabulary, Vocabulary
from anamnesis.domain.types import TermId
from anamnesis.infrastructure.reasoning.ontology import (
    REPRESENTATIVE_SUFFIX,
    open_ontology,
    representatives,
)


_RESERVED_CLASSES: Final[tuple[str, ...]] = (
    "RiskMarker",
    "SelfHarmThoughts",
    "UrgentMedicalMarker",
)
"""Классы, понятия которых утверждает только детерминированный контур."""


class OwlOntologyVocabulary(IOntologyVocabulary):
    """Понятия проявлений и стрессоров, прочитанные из онтологии один раз при запуске."""

    def __init__(self, vocabulary: Vocabulary) -> None:
        self._vocabulary: Vocabulary = vocabulary

    @classmethod
    def load(cls, path: Path) -> "OwlOntologyVocabulary":
        with open_ontology(path) as ontology:
            vocabulary: Vocabulary = Vocabulary(
                manifestations=representatives(ontology.Manifestation.instances()),
                stressors=representatives(ontology.Stressor.instances()),
                reserved=frozenset().union(
                    *(representatives(ontology[name].instances()) for name in _RESERVED_CLASSES),
                ),
                concepts=cls._concepts(ontology),
            )

        return cls(vocabulary)

    @classmethod
    def _concepts(cls, ontology: Any) -> Mapping[TermId, TermId]:
        """Понятие каждого термина проявлений и стрессоров, у которого оно есть."""
        concepts: Mapping[TermId, TermId] = MappingProxyType(
            {
                TermId(individual.name): concept
                for kind in (ontology.Manifestation, ontology.Stressor)
                for individual in kind.instances()
                if (concept := cls._concept(individual)) is not None
            },
        )
        return concepts

    @staticmethod
    def _concept(individual: Any) -> TermId | None:
        """Представитель класса, к которому относится термин."""
        for concept_class in individual.is_a:
            name: str = f"{concept_class.name}{REPRESENTATIVE_SUFFIX}"
            if concept_class.namespace.ontology[name] is not None:
                return TermId(name)
        return None

    @override
    def vocabulary(self) -> Vocabulary:
        return self._vocabulary
