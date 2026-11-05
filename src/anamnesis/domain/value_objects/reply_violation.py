from typing import ClassVar

from anamnesis.domain.enums.violation_kind import ViolationKind
from anamnesis.domain.errors.common import ValidationError
from anamnesis.domain.value_objects.base import ValueObject, value_object


@value_object
class ReplyViolation(ValueObject):
    """Недопустимый фрагмент ответа системы.

    Attributes:
        kind: Вид нарушения.
        quote: Фрагмент ответа.
    """

    _FIELD_NAME: ClassVar[str] = "ReplyViolation"

    kind: ViolationKind
    quote: str

    def __post_init__(self) -> None:
        self._normalize()
        self._validate()

    def _normalize(self) -> None:
        self._set("quote", self.quote.strip())

    def _validate(self) -> None:
        if not self.quote:
            raise ValidationError(field=self._FIELD_NAME, reason="quote must not be empty")
