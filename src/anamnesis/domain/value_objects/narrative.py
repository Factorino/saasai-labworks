from typing import ClassVar

from anamnesis.domain.errors.common import ValidationError
from anamnesis.domain.value_objects.base import ValueObject, value_object


@value_object
class Narrative(ValueObject):
    """Текст сводки, написанный для человека.

    Attributes:
        description: Состояние простыми словами, без клинических ярлыков.
        request: Запрос к специалисту от первого лица.
    """

    _FIELD_NAME: ClassVar[str] = "Narrative"

    description: str
    request: str

    def __post_init__(self) -> None:
        self._normalize()
        self._validate()

    def _normalize(self) -> None:
        self._set("description", self.description.strip())
        self._set("request", self.request.strip())

    def _validate(self) -> None:
        if not self.description or not self.request:
            raise ValidationError(field=self._FIELD_NAME, reason="texts must not be empty")
