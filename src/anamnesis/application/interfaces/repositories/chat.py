from abc import abstractmethod
from typing import Protocol

from anamnesis.domain.entities.chat import Chat, ChatId


class IChatRepository(Protocol):
    @abstractmethod
    async def find_by_id(self, chat_id: ChatId) -> Chat | None: ...

    @abstractmethod
    async def save(self, chat: Chat) -> None: ...

    @abstractmethod
    async def delete(self, chat_id: ChatId) -> bool: ...
