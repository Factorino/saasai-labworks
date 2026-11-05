from copy import deepcopy
from typing import override

from anamnesis.application.interfaces.repositories.chat import IChatRepository
from anamnesis.domain.entities.chat import Chat, ChatId


class InMemoryChatRepository(IChatRepository):
    def __init__(self) -> None:
        self._chats: dict[ChatId, Chat] = {}

    @override
    async def find_by_id(self, chat_id: ChatId) -> Chat | None:
        chat: Chat | None = self._chats.get(chat_id)
        return deepcopy(chat) if chat is not None else None

    @override
    async def save(self, chat: Chat) -> None:
        self._chats[chat.id] = deepcopy(chat)

    @override
    async def delete(self, chat_id: ChatId) -> bool:
        return self._chats.pop(chat_id, None) is not None
