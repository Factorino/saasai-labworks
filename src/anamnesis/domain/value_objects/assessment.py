from typing import ClassVar

from anamnesis.domain.enums.fact_kind import FactKind
from anamnesis.domain.enums.referral import Referral
from anamnesis.domain.enums.urgency_level import UrgencyLevel
from anamnesis.domain.errors.common import ValidationError
from anamnesis.domain.types import RuleId, TermId
from anamnesis.domain.value_objects.base import ValueObject, value_object
from anamnesis.domain.value_objects.crisis_signal import CrisisSignal
from anamnesis.domain.value_objects.inference import PracticeAdvice


@value_object
class Assessment(ValueObject):
    """Итог оценки случая — основа сводки.

    Собирается `AssessmentService` по результату вывода. Что показать
    в сводке, следует из уровня и направлений (`self_help`).

    Attributes:
        level: Итоговый уровень; `None` — «недостаточно данных».
        crisis: Кризисный сценарий; возможен только с L3.
        fired_rules: Сработавшие правила по порядку — для объяснения.
        clusters: Кластеры по порядку — для объяснения.
        practices: Все выведенные практики. Советовать можно только
            `advised_practices`.
        referrals: Куда обратиться за помощью, в порядке показа.
        signals: Находки кризисного детектора за диалог.
        missing: Обязательные сведения, которых не хватило.
    """

    _FIELD_NAME: ClassVar[str] = "Assessment"

    level: UrgencyLevel | None
    crisis: bool = False
    fired_rules: tuple[RuleId, ...] = ()
    clusters: tuple[TermId, ...] = ()
    practices: tuple[PracticeAdvice, ...] = ()
    referrals: tuple[Referral, ...] = ()
    signals: tuple[CrisisSignal, ...] = ()
    missing: frozenset[FactKind] = frozenset()

    def __post_init__(self) -> None:
        self._validate()

    def _validate(self) -> None:
        if self.crisis and self.level is not UrgencyLevel.L3:
            raise ValidationError(field=self._FIELD_NAME, reason="a crisis must have level L3")

    @property
    def insufficient_data(self) -> bool:
        """Уровень оценить не удалось."""
        return self.level is None

    @property
    def is_complete(self) -> bool:
        """Все обязательные сведения собраны."""
        return not self.missing

    @property
    def self_help(self) -> bool:
        """Можно ли советовать самопомощь.

        При L3 основной совет — срочная помощь, при направлении на скорую —
        она. В обоих случаях практики и формулировка L0 о самопомощи
        не показываются.
        """
        return (
            self.level is not UrgencyLevel.L3
            and Referral.EMERGENCY_MEDICAL_CARE not in self.referrals
        )

    @property
    def advised_practices(self) -> tuple[PracticeAdvice, ...]:
        """Практики для сводки: все выведенные или ни одной."""
        return self.practices if self.self_help else ()
