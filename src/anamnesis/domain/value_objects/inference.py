from typing import override

from anamnesis.domain.enums.recommendation import Referral, UrgencyLevel
from anamnesis.domain.types import RuleId, TermId
from anamnesis.domain.value_objects.base import ValueObject, value_object
from anamnesis.domain.value_objects.practice import PracticeAdvice


@value_object
class InferenceResult(ValueObject):
    """Что утвердила машина вывода по одному случаю.

    Граница между доменом и онтологией.

    Attributes:
        levels: Уровни из `hasUrgencyLevel`.
        fired_rules: Сработавшие правила из `firedRule`; нужны для объяснения.
        clusters: Кластеры из `indicatesCluster` (`AnxietyCluster_`, …).
        practices: Практики из `suggestsPractice`.
        referrals: Направления из `suggestsReferral`.
    """

    levels: frozenset[UrgencyLevel] = frozenset()

    fired_rules: frozenset[RuleId] = frozenset()
    clusters: frozenset[TermId] = frozenset()

    practices: tuple[PracticeAdvice, ...] = ()
    referrals: frozenset[Referral] = frozenset()

    @override
    def _normalize(self) -> None:
        unique: dict[TermId, PracticeAdvice] = {}
        for advice in self.practices:
            unique.setdefault(advice.practice, advice)

        practices: tuple[PracticeAdvice, ...] = tuple(
            sorted(unique.values(), key=lambda a: a.practice)
        )
        self._set("practices", practices)
