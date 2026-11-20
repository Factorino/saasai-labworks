from abc import abstractmethod
from typing import ClassVar, Protocol

from pydantic import Field, SerializeAsAny

from anamnesis.application.dto.base import DTO


class ModelData(DTO):
    """Основа данных задачи для языковой модели.

    Имена полей — ключи входного JSON, на которые ссылаются инструкции, поэтому
    менять их можно только вместе с инструкциями.
    """

    _abstract_: ClassVar[bool] = True


class ModelRequest(DTO):
    """Запрос к языковой модели.

    Инструкция и данные разделены: инструкция берётся только из фиксированных
    файлов, а всё, что написал пользователь, попадает в данные. Как доставить
    данные модели, чтобы текст пользователя не читался как инструкция, решает
    реализация `ILanguageModel`.

    Attributes:
        instruction: Фиксированная инструкция задачи.
        data: Данные задачи.
        rejected_fragments: Фрагменты прошлого ответа, отклонённые проверкой;
            передаются вместе с данными под этим же ключом.
        temperature: Температура выборки; `None` — по умолчанию модели.
    """

    instruction: str
    data: SerializeAsAny[ModelData]
    rejected_fragments: tuple[str, ...] = ()
    temperature: float | None = Field(default=None, ge=0, le=2)


class ILanguageModel(Protocol):
    @abstractmethod
    async def complete_structured[OutputT: DTO](
        self,
        request: ModelRequest,
        output: type[OutputT],
    ) -> OutputT:
        """Ответ модели по схеме `output`.

        Raises:
            LanguageModelUnavailableError: Модель недоступна.
            LanguageModelReplyError: Ответ не соответствует схеме.
        """
