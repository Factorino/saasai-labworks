from collections import deque
from collections.abc import Mapping
from typing import Final, override

from dishka import Provider, Scope
import pydantic

from anamnesis.application.dto.base import DTO
from anamnesis.application.errors.llm import (
    LanguageModelReplyError,
    LanguageModelUnavailableError,
)
from anamnesis.application.interfaces.llm.language_model import (
    ILanguageModel,
    ModelRequest,
)


MODEL_NAME: Final[str] = "scripted"
"""Имя модели в ошибках заглушки."""

type ScriptedReply = Mapping[str, object] | LanguageModelUnavailableError | LanguageModelReplyError
"""Заготовка ответа: поля ответа по схеме задачи или сбой, который модель выбросит."""


class ScriptedModel(ILanguageModel):
    """Языковая модель по сценарию теста.

    Ответы заготавливаются по задачам: задача — схема ответа (`ExtractionReply`,
    `NarrativeReply`, `AnswerReply`). Заготовка проверяется схемой, которую
    передал сервис, как у настоящего адаптера: ответ не по схеме даёт
    `LanguageModelReplyError`. Если заготовок для задачи не осталось, модель
    недоступна. Все запросы запоминаются вместе со схемой.

    Attributes:
        requests: Запросы по порядку: схема ответа и запрос.
    """

    def __init__(self) -> None:
        self.requests: list[tuple[type[DTO], ModelRequest]] = []
        self._replies: dict[type[DTO], deque[ScriptedReply]] = {}

    @override
    async def complete_structured[OutputT: DTO](
        self,
        request: ModelRequest,
        output: type[OutputT],
    ) -> OutputT:
        self.requests.append((output, request))
        reply: ScriptedReply = self._next_reply(output)

        if isinstance(reply, LanguageModelUnavailableError | LanguageModelReplyError):
            raise reply

        try:
            validated: OutputT = output.model_validate(reply)
        except pydantic.ValidationError as error:
            raise LanguageModelReplyError(model=MODEL_NAME, reason=str(error)) from error
        return validated

    def script(self, task: type[DTO], *replies: ScriptedReply) -> None:
        """Добавляет ответы задачи; они отдаются по порядку."""
        self._replies.setdefault(task, deque()).extend(replies)

    def reset(self) -> None:
        """Забывает заготовки и запросы: каждый тест начинает с недоступной модели."""
        self.requests.clear()
        self._replies.clear()

    def requests_for(self, task: type[DTO]) -> list[ModelRequest]:
        """Запросы задачи; схема извлечения строится сервисом как подкласс `task`."""
        found: list[ModelRequest] = [
            request for output, request in self.requests if issubclass(output, task)
        ]
        return found

    def _next_reply(self, output: type[DTO]) -> ScriptedReply:
        """Следующая заготовка задачи или недоступность, если их нет."""
        for task, replies in self._replies.items():
            if issubclass(output, task) and replies:
                return replies.popleft()

        raise LanguageModelUnavailableError(model=MODEL_NAME, reason="no scripted reply")


def model_provider(model: ScriptedModel) -> Provider:
    def language_model() -> ILanguageModel:
        return model

    provider: Provider = Provider(scope=Scope.APP)
    provider.provide(language_model, provides=ILanguageModel, override=True)
    return provider
