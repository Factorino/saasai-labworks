from collections.abc import Mapping
import json
from typing import Any, Final

from anamnesis.domain.enums.message_role import MessageRole
from anamnesis.domain.value_objects.message import Message


_DATA_OPEN: Final[str] = "<data>"
_DATA_CLOSE: Final[str] = "</data>"


def data_message(data: Mapping[str, Any]) -> Message:
    """Данные для модели: JSON внутри явных разделителей.

    Инструкции модель получает отдельно и только из фиксированных файлов, а всё,
    что написал пользователь, попадает сюда. В JSON угловая скобка заменяется
    равнозначной escape-последовательностью, поэтому реплика не может закрыть
    разделитель.
    """
    content: str = json.dumps(data, ensure_ascii=False).replace("<", "\\u003c")
    return Message(role=MessageRole.USER, text=f"{_DATA_OPEN}\n{content}\n{_DATA_CLOSE}")
