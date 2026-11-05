from typing import ClassVar

from anamnesis.domain.errors.common import ValidationError
from anamnesis.domain.value_objects.base import ValueObject, value_object


@value_object
class Duration(ValueObject):
    """Сколько длятся проявления."""

    _FIELD_NAME: ClassVar[str] = "Duration"

    _MAX_WEEKS: ClassVar[int] = 520

    weeks: int

    def __post_init__(self) -> None:
        self._validate()

    def _validate(self) -> None:
        if not 0 <= self.weeks <= self._MAX_WEEKS:
            raise ValidationError(
                field=self._FIELD_NAME,
                reason=f"must be between 0 and {self._MAX_WEEKS} weeks",
            )
