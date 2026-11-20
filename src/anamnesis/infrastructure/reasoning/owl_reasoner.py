import asyncio
from collections.abc import Iterable, Mapping
from pathlib import Path
from types import MappingProxyType
from typing import Any, Final, override

from anamnesis.application.errors.knowledge import UnknownTermError
from anamnesis.application.interfaces.reasoning.case_reasoner import ICaseReasoner
from anamnesis.domain.enums.recommendation import Referral, UrgencyLevel
from anamnesis.domain.types import RuleId, TermId
from anamnesis.domain.value_objects.case_facts import CaseFacts
from anamnesis.domain.value_objects.inference import InferenceResult
from anamnesis.domain.value_objects.practice import PracticeAdvice
from anamnesis.infrastructure.reasoning.ontology import (
    REPRESENTATIVE_SUFFIX,
    open_ontology,
    representatives,
    run_pellet,
)


_LEVELS: Final[Mapping[str, UrgencyLevel]] = MappingProxyType(
    {f"{level.name}{REPRESENTATIVE_SUFFIX}": level for level in UrgencyLevel},
)
"""Представители уровней: `L0_`–`L3_`."""

_REFERRALS: Final[Mapping[str, Referral]] = MappingProxyType(
    {
        "".join(part.capitalize() for part in referral.value.split("_"))
        + REPRESENTATIVE_SUFFIX: referral
        for referral in Referral
    },
)
"""Представители ветви `Referral` по кодам: `doctor_visit` → `DoctorVisit_`."""

_CASE_NAME: Final[str] = "case"
"""Имя индивида `Case`; в каждом мире он один."""


class OwlCaseReasoner(ICaseReasoner):
    """Вывод по SWRL-правилам онтологии машиной Pellet (owlready2)."""

    def __init__(
        self,
        *,
        ontology_path: Path,
        max_concurrency: int = 1,
    ) -> None:
        self._ontology_path: Path = ontology_path
        self._semaphore: asyncio.Semaphore = asyncio.Semaphore(max_concurrency)

    @classmethod
    def load(cls, path: Path, *, max_concurrency: int = 1) -> "OwlCaseReasoner":
        with open_ontology(path) as ontology:
            cls._validate_names(ontology)

        return cls(ontology_path=path, max_concurrency=max_concurrency)

    @classmethod
    def _build_case(cls, ontology: Any, facts: CaseFacts) -> Any:
        """Индивид `Case` со сведениями: термины — объектные свойства, шкалы — данные."""
        with ontology:
            case: Any = ontology.Case(_CASE_NAME)
            case.hasManifestation = cls._individuals(
                ontology, facts.manifestation_terms, ontology.Manifestation
            )
            case.hasStressor = cls._individuals(ontology, facts.stressor_terms, ontology.Stressor)
            case.affectsDomain = cls._individuals(
                ontology, facts.affected_domains, ontology.LifeDomain
            )
            if facts.duration is not None:
                case.durationWeeks = [facts.duration.weeks]
            if facts.frequency is not None:
                case.frequency = [int(facts.frequency)]
            if facts.impact is not None:
                case.impactDegree = [int(facts.impact)]
            if facts.self_harm is not None:
                case.selfHarmScreening = [str(facts.self_harm)]

        return case

    @classmethod
    def _read_result(cls, case: Any) -> InferenceResult:
        """Выведенное правилами для случая."""
        result: InferenceResult = InferenceResult(
            levels=frozenset(_LEVELS[level.name] for level in case.hasUrgencyLevel),
            fired_rules=frozenset(RuleId(rule.name) for rule in case.firedRule),
            clusters=frozenset(TermId(cluster.name) for cluster in case.indicatesCluster),
            practices=tuple(cls._practice(case, practice) for practice in case.suggestsPractice),
            referrals=frozenset(_REFERRALS[referral.name] for referral in case.suggestsReferral),
        )
        return result

    @classmethod
    def _practice(cls, case: Any, practice: Any) -> PracticeAdvice:
        """Практика, её ограничения (`cautionFor`) в случае и подходящие кластеры."""
        advice: PracticeAdvice = PracticeAdvice(
            practice=TermId(practice.name),
            cautions=frozenset(
                TermId(concept.name)
                for concept in practice.cautionFor
                if cls._present(case, concept)
            ),
            clusters=frozenset(
                TermId(cluster.name)
                for cluster in case.indicatesCluster
                if practice in cluster.recommendsPractice
            ),
        )
        return advice

    @staticmethod
    def _validate_names(ontology: Any) -> None:
        """Представители уровней и направлений в онтологии, члены перечислений домена."""
        branches: tuple[tuple[str, Any, Mapping[str, object]], ...] = (
            ("UrgencyLevel", ontology.UrgencyLevel, _LEVELS),
            ("Referral", ontology.Referral, _REFERRALS),
        )

        for branch, ontology_class, expected in branches:
            root: str = f"{ontology_class.name}{REPRESENTATIVE_SUFFIX}"
            found: frozenset[TermId] = representatives(ontology_class.instances()) - {root}
            if found != expected.keys():
                raise ValueError(
                    f"Ontology {branch} representatives {sorted(found)} "
                    f"do not match the domain {sorted(expected)}",
                )

    @staticmethod
    def _individuals(ontology: Any, terms: Iterable[TermId], kind: Any) -> list[Any]:
        """Индивиды терминов; термин не той ветви считается неизвестным."""
        individuals: list[Any] = []

        for term in terms:
            individual: Any = ontology[term]
            if individual is None or not isinstance(individual, kind):
                raise UnknownTermError(term=term)
            individuals.append(individual)

        return individuals

    @staticmethod
    def _present(case: Any, concept: Any) -> bool:
        """Есть ли понятие в случае.

        `concept` — представитель класса: кластер есть, если он выведен;
        проявление или стрессор — если в случае есть термин этого класса.
        """
        if concept in case.indicatesCluster:
            return True

        classes: list[Any] = list(concept.is_a)
        return any(
            isinstance(term, concept_class)
            for term in [*case.hasManifestation, *case.hasStressor]
            for concept_class in classes
        )

    @override
    async def infer(self, facts: CaseFacts) -> InferenceResult:
        async with self._semaphore:
            return await asyncio.to_thread(self._infer, facts)

    def _infer(self, facts: CaseFacts) -> InferenceResult:
        """Вывод в отдельном мире: загрузка онтологии, индивид случая, Pellet, результат."""
        with open_ontology(self._ontology_path) as ontology:
            case: Any = self._build_case(ontology, facts)
            run_pellet(ontology)
            result: InferenceResult = self._read_result(case)

        return result
