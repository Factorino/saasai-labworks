from typing import TYPE_CHECKING

from anamnesis.domain.enums.recommendation import Referral, UrgencyLevel
from anamnesis.domain.value_objects.assessment import Assessment
from anamnesis.domain.value_objects.case_facts import CaseFacts
from anamnesis.domain.value_objects.crisis_signal import CrisisSignal
from anamnesis.domain.value_objects.inference import InferenceResult


if TYPE_CHECKING:
    from anamnesis.domain.types import RuleId, TermId


class AssessmentService:
    """Итоговая оценка случая по результату вывода.

    SWRL-правила только утверждают: в открытом мире OWL не выразить ни
    «правило не сработало — срочности нет», ни выбор максимума. Поэтому
    итоговый уровень выбирается здесь.
    """

    @staticmethod
    def _level(
        facts: CaseFacts,
        inference: InferenceResult,
        *,
        crisis: bool,
    ) -> UrgencyLevel | None:
        """Итоговый уровень.

        - кризис -> L3: его фиксирует и сам чат, без онтологии;
        - иначе максимум утверждённых правилами уровней;
        - уровней нет, но обязательные сведения полны -> L0;
        - иначе `None`, «недостаточно данных».
        """
        if crisis:
            return UrgencyLevel.L3
        if inference.levels:
            return max(inference.levels)
        if facts.is_complete:
            return UrgencyLevel.L0
        return None

    @staticmethod
    def _referrals(
        inference: InferenceResult,
        level: UrgencyLevel | None,
        signals: tuple[CrisisSignal, ...],
    ) -> tuple[Referral, ...]:
        """Направления в порядке показа.

        Службы помощи добавляются при L3 и при любой находке детектора, даже
        если правила их не вывели: кризис мог быть найден вне онтологии.
        """
        referrals: set[Referral] = set(inference.referrals)
        if level is UrgencyLevel.L3 or signals:
            referrals.add(Referral.CRISIS_HELPLINE)
        ordered: tuple[Referral, ...] = tuple(r for r in Referral if r in referrals)
        return ordered

    def assess(
        self,
        facts: CaseFacts,
        inference: InferenceResult,
        *,
        crisis: bool = False,
        signals: tuple[CrisisSignal, ...] = (),
    ) -> Assessment:
        """Собирает оценку случая.

        Args:
            facts: Что известно о случае.
            inference: Что утвердила машина вывода.
            crisis: Чат в кризисном сценарии.
            signals: Находки кризисного детектора за диалог.

        Returns:
            Оценка с уровнем, объяснением, практиками и направлениями.
        """
        level: UrgencyLevel | None = self._level(facts, inference, crisis=crisis)
        fired_rules: tuple[RuleId, ...] = tuple(sorted(inference.fired_rules))
        clusters: tuple[TermId, ...] = tuple(sorted(inference.clusters))
        refferals: tuple[Referral, ...] = self._referrals(inference, level, signals)
        return Assessment(
            level=level,
            crisis=crisis,
            fired_rules=fired_rules,
            clusters=clusters,
            practices=inference.practices,
            referrals=refferals,
            signals=signals,
            missing=facts.missing_required,
        )
