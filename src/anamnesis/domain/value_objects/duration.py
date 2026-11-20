from typing import ClassVar, override

from anamnesis.domain.errors.common import ValidationError
from anamnesis.domain.value_objects.base import ValueObject, value_object


@value_object
class Duration(ValueObject):
    """Сколько длятся проявления."""

    MAX_WEEKS: ClassVar[int] = 520

    weeks: int

    @override
    def _validate(self) -> None:
        if not 0 <= self.weeks <= self.MAX_WEEKS:
            raise ValidationError(
                subject=self._type_name,
                reason=f"must be between 0 and {self.MAX_WEEKS} weeks",
            )
