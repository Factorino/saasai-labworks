from typing import override

from anamnesis.application.dto.base import DTO
from anamnesis.application.dto.views.reply import ReplyView
from anamnesis.application.errors.chat import ChatNotFoundError
from anamnesis.application.interfaces.common.interactor import Interactor
from anamnesis.application.interfaces.repositories.chat import IChatRepository
from anamnesis.application.services.dialogue import DialogueService
from anamnesis.domain.entities.chat import Chat, ChatId


class FinishChatRequest(DTO):
    chat_id: ChatId


class FinishChatResponse(DTO):
    reply: ReplyView


class FinishChat(Interactor[FinishChatRequest, FinishChatResponse]):
    def __init__(self, *, chat_repository: IChatRepository, dialogue: DialogueService) -> None:
        self._chat_repo: IChatRepository = chat_repository
        self._dialogue: DialogueService = dialogue

    @override
    async def execute(self, request: FinishChatRequest) -> FinishChatResponse:
        chat: Chat | None = await self._chat_repo.find_by_id(request.chat_id)
        if chat is None:
            raise ChatNotFoundError(value=request.chat_id)

        chat.finish()
        reply: ReplyView = await self._dialogue.advance(chat)
        await self._chat_repo.save(chat)
        return FinishChatResponse(reply=reply)
