from abc import abstractmethod
from typing import Protocol

from pydantic import Field

from anamnesis.application.dto.base import DTO
from anamnesis.domain.value_objects.message import Message


class ModelRequest(DTO):
    instruction: str
    messages: tuple[Message, ...] = ()
    temperature: float | None = Field(default=None, ge=0, le=2)


class ILanguageModel(Protocol):
    @abstractmethod
    async def complete_structured[OutputT: DTO](
        self,
        request: ModelRequest,
        output: type[OutputT],
    ) -> OutputT: ...
