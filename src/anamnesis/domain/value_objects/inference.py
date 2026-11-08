from anamnesis.domain.enums.referral import Referral
from anamnesis.domain.enums.urgency_level import UrgencyLevel
from anamnesis.domain.types import RuleId, TermId
from anamnesis.domain.value_objects.base import ValueObject, value_object


@value_object
class PracticeAdvice(ValueObject):
    """Практика, которую правила предложили случаю, и её ограничения.

    Attributes:
        practice: Представитель практики (`BreathingPractice_`), выведенный
            через `suggestsPractice`.
        cautions: Понятия из `cautionFor` практики, которые есть в случае.
        clusters: Кластеры случая, которым практика подходит.
    """

    practice: TermId
    cautions: frozenset[TermId] = frozenset()
    clusters: frozenset[TermId] = frozenset()

    @property
    def needs_caution(self) -> bool:
        """Показывать ли практику только с предупреждением."""
        return bool(self.cautions)


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

    def __post_init__(self) -> None:
        self._normalize()

    def _normalize(self) -> None:
        unique: dict[TermId, PracticeAdvice] = {}
        for advice in self.practices:
            unique.setdefault(advice.practice, advice)
        self._set("practices", tuple(sorted(unique.values(), key=lambda a: a.practice)))
