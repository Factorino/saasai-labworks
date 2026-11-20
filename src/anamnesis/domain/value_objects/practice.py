from typing import override

from anamnesis.domain.errors.common import ValidationError
from anamnesis.domain.types import TermId
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
class LevelSelection(ValueObject):
    """Подбор практик на одном уровне срочности.

    Attributes:
        limit: Сколько практик показать.
        excluded: Практики, которые на этом уровне не советуются.
    """

    limit: int
    excluded: frozenset[TermId] = frozenset()

    @override
    def _validate(self) -> None:
        if self.limit < 1:
            raise ValidationError(subject=self._type_name, reason="limit must be positive")
