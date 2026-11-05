from typing import ClassVar

from anamnesis.domain.enums.message_role import MessageRole
from anamnesis.domain.errors.common import ValidationError
from anamnesis.domain.value_objects.base import ValueObject, value_object


@value_object
class Message(ValueObject):
    _FIELD_NAME: ClassVar[str] = "Message"

    role: MessageRole
    text: str

    def __post_init__(self) -> None:
        self._normalize()
        self._validate()

    def _normalize(self) -> None:
        self._set("text", self.text.strip())

    def _validate(self) -> None:
        if not self.text:
            raise ValidationError(field=self._FIELD_NAME, reason="text must not be empty")
