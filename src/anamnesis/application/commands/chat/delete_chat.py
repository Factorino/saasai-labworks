from typing import override

from anamnesis.application.dto.base import DTO
from anamnesis.application.errors.chat import ChatNotFoundError
from anamnesis.application.interfaces.common.interactor import Interactor
from anamnesis.application.interfaces.repositories.chat import IChatRepository
from anamnesis.domain.entities.chat import ChatId


class DeleteChatRequest(DTO):
    chat_id: ChatId


class DeleteChat(Interactor[DeleteChatRequest, None]):
    def __init__(self, *, chat_repository: IChatRepository) -> None:
        self._chat_repo: IChatRepository = chat_repository

    @override
    async def execute(self, request: DeleteChatRequest) -> None:
        if not await self._chat_repo.delete(request.chat_id):
            raise ChatNotFoundError(value=request.chat_id)
