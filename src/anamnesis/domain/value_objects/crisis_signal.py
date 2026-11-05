from typing import ClassVar

from anamnesis.domain.enums.crisis_category import CrisisCategory
from anamnesis.domain.errors.common import ValidationError
from anamnesis.domain.value_objects.base import ValueObject, value_object


@value_object
class CrisisSignal(ValueObject):
    """Находка кризисного детектора и цитата, на которой она основана.

    Attributes:
        category: Что найдено.
        quote: Фрагмент реплики.
    """

    _FIELD_NAME: ClassVar[str] = "CrisisSignal"

    category: CrisisCategory
    quote: str

    def __post_init__(self) -> None:
        self._normalize()
        self._validate()

    def _normalize(self) -> None:
        self._set("quote", self.quote.strip())

    def _validate(self) -> None:
        if not self.quote:
            raise ValidationError(field=self._FIELD_NAME, reason="quote must not be empty")
