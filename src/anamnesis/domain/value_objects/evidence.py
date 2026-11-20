from typing import override

from anamnesis.domain.errors.common import ValidationError
from anamnesis.domain.types import TermId
from anamnesis.domain.value_objects.base import ValueObject, value_object


@value_object
class Evidence(ValueObject):
    """Найденный термин онтологии и цитата, на которой он основан.

    Attributes:
        term: Термин онтологии: проявление (`Manifestation`) или стрессор (`Stressor`).
        quote: Фрагмент реплики. Пуст, если сведения переданы напрямую, без текста.
    """

    term: TermId
    quote: str = ""

    @override
    def _normalize(self) -> None:
        self._set("term", TermId(self.term.strip()))
        self._set("quote", self.quote.strip())

    @override
    def _validate(self) -> None:
        if not self.term:
            raise ValidationError(subject=self._type_name, reason="term must not be empty")
