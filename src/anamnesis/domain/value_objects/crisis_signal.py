from typing import override

from anamnesis.domain.enums.crisis import CrisisCategory
from anamnesis.domain.errors.common import ValidationError
from anamnesis.domain.value_objects.base import ValueObject, value_object


@value_object
class CrisisSignal(ValueObject):
    """Находка кризисного детектора и цитата, на которой она основана.

    Attributes:
        category: Что найдено.
        quote: Фрагмент реплики.
    """

    category: CrisisCategory
    quote: str

    @override
    def _normalize(self) -> None:
        self._set("quote", self.quote.strip())

    @override
    def _validate(self) -> None:
        if not self.quote:
            raise ValidationError(subject=self._type_name, reason="quote must not be empty")
