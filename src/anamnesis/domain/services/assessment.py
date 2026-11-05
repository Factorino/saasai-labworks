from anamnesis.domain.enums.referral import Referral
from anamnesis.domain.enums.urgency_level import UrgencyLevel
from anamnesis.domain.value_objects.assessment import Assessment
from anamnesis.domain.value_objects.case_facts import CaseFacts
from anamnesis.domain.value_objects.crisis_signal import CrisisSignal
from anamnesis.domain.value_objects.inference import InferenceResult


class AssessmentService:
    """Итоговая оценка случая по результату вывода.

    SWRL-правила только утверждают: в открытом мире OWL не выразить ни
    «правило не сработало — срочности нет», ни выбор максимума. Поэтому
    итоговый уровень выбирается здесь.
    """

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
        return Assessment(
            level=level,
            crisis=crisis,
            fired_rules=tuple(sorted(inference.fired_rules)),
            clusters=tuple(sorted(inference.clusters)),
            practices=inference.practices,
            referrals=self._referrals(inference, level, signals),
            signals=signals,
            missing=facts.missing_required,
        )

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
        return tuple(referral for referral in Referral if referral in referrals)
