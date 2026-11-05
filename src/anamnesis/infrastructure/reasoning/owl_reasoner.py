import asyncio
from collections.abc import Iterable, Mapping
from pathlib import Path
from types import MappingProxyType
from typing import Any, Final, override

from owlready2 import World, sync_reasoner_pellet

from anamnesis.application.errors.knowledge import UnknownTermError
from anamnesis.application.interfaces.reasoning.case_reasoner import ICaseReasoner
from anamnesis.domain.enums.referral import Referral
from anamnesis.domain.enums.urgency_level import UrgencyLevel
from anamnesis.domain.types import RuleId, TermId
from anamnesis.domain.value_objects.case_facts import CaseFacts
from anamnesis.domain.value_objects.inference import InferenceResult, PracticeAdvice


_LEVELS: Final[Mapping[str, UrgencyLevel]] = MappingProxyType(
    {f"{level.name}_": level for level in UrgencyLevel},
)
"""Представители уровней `L0_`–`L3_`."""

_REFERRALS: Final[Mapping[str, Referral]] = MappingProxyType(
    {
        "EmergencyMedicalCare_": Referral.EMERGENCY_MEDICAL_CARE,
        "CrisisHelpline_": Referral.CRISIS_HELPLINE,
        "DoctorVisit_": Referral.DOCTOR_VISIT,
    },
)
"""Представители ветви `Referral`."""

_CASE_NAME: Final[str] = "case"
"""Имя индивида `Case`; в каждом мире он один."""


class OwlCaseReasoner(ICaseReasoner):
    """Вывод по SWRL-правилам онтологии машиной Pellet (owlready2).

    Каждый вывод идёт в отдельном мире owlready2: онтология загружается заново
    (сотые доли секунды), поэтому случаи не влияют друг на друга. Pellet
    работает в отдельном процессе Java; число одновременных выводов
    ограничено.
    """

    def __init__(self, *, ontology_path: Path, max_concurrency: int = 1) -> None:
        self._ontology_iri: str = ontology_path.resolve().as_uri()
        self._semaphore: asyncio.Semaphore = asyncio.Semaphore(max_concurrency)

    @override
    async def infer(self, facts: CaseFacts) -> InferenceResult:
        async with self._semaphore:
            return await asyncio.to_thread(self._infer, facts)

    def _infer(self, facts: CaseFacts) -> InferenceResult:
        world: Any = World()
        try:
            onto: Any = world.get_ontology(self._ontology_iri).load()
            case: Any = self._build_case(onto, facts)
            sync_reasoner_pellet(
                world,
                infer_property_values=True,
                infer_data_property_values=True,
                debug=0,
            )
            return self._read_result(case)
        finally:
            world.close()

    @classmethod
    def _build_case(cls, onto: Any, facts: CaseFacts) -> Any:
        """Индивид `Case` со сведениями: термины — объектные свойства, шкалы — данные."""
        with onto:
            case: Any = onto.Case(_CASE_NAME)
            case.hasManifestation = cls._individuals(
                onto, facts.manifestation_terms, onto.Manifestation
            )
            case.hasStressor = cls._individuals(onto, facts.stressor_terms, onto.Stressor)
            case.affectsDomain = cls._individuals(onto, facts.affected_domains, onto.LifeDomain)
            if facts.duration is not None:
                case.durationWeeks = [facts.duration.weeks]
            if facts.frequency is not None:
                case.frequency = [int(facts.frequency)]
            if facts.impact is not None:
                case.impactDegree = [int(facts.impact)]
            if facts.self_harm is not None:
                case.selfHarmScreening = [str(facts.self_harm)]
        return case

    @staticmethod
    def _individuals(onto: Any, terms: Iterable[TermId], kind: Any) -> list[Any]:
        """Индивиды терминов; термин не той ветви считается неизвестным.

        Raises:
            UnknownTermError: Термина нет в онтологии или он из другой ветви.
        """
        individuals: list[Any] = []
        for term in terms:
            individual: Any = onto[term]
            if individual is None or not isinstance(individual, kind):
                raise UnknownTermError(term=term)
            individuals.append(individual)
        return individuals

    @classmethod
    def _read_result(cls, case: Any) -> InferenceResult:
        return InferenceResult(
            levels=frozenset(_LEVELS[level.name] for level in case.hasUrgencyLevel),
            fired_rules=frozenset(RuleId(rule.name) for rule in case.firedRule),
            clusters=frozenset(TermId(cluster.name) for cluster in case.indicatesCluster),
            practices=tuple(cls._practice(case, practice) for practice in case.suggestsPractice),
            referrals=frozenset(_REFERRALS[referral.name] for referral in case.suggestsReferral),
        )

    @classmethod
    def _practice(cls, case: Any, practice: Any) -> PracticeAdvice:
        """Практика и те её ограничения (`cautionFor`), которые есть в случае."""
        return PracticeAdvice(
            practice=TermId(practice.name),
            cautions=frozenset(
                TermId(concept.name)
                for concept in practice.cautionFor
                if cls._present(case, concept)
            ),
        )

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
