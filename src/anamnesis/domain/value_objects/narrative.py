from typing import override

from anamnesis.domain.errors.common import ValidationError
from anamnesis.domain.value_objects.base import ValueObject, value_object


@value_object
class Narrative(ValueObject):
    """Текст сводки, написанный для человека.

    Attributes:
        description: Состояние простыми словами, без клинических ярлыков.
        request: Запрос к специалисту от первого лица.
    """

    description: str
    request: str

    @override
    def _normalize(self) -> None:
        self._set("description", self.description.strip())
        self._set("request", self.request.strip())

    @override
    def _validate(self) -> None:
        if not self.description or not self.request:
            raise ValidationError(subject=self._type_name, reason="texts must not be empty")
