from typing import override

from anamnesis.domain.enums.chat import MessageRole
from anamnesis.domain.errors.common import ValidationError
from anamnesis.domain.value_objects.base import ValueObject, value_object


@value_object
class Message(ValueObject):
    """Реплика в истории диалога.

    Attributes:
        role: Автор реплики.
        text: Текст на языке диалога.
    """

    role: MessageRole
    text: str

    @override
    def _normalize(self) -> None:
        self._set("text", self.text.strip())

    @override
    def _validate(self) -> None:
        if not self.text:
            raise ValidationError(subject=self._type_name, reason="text must not be empty")
