from typing import override

from anamnesis.application.dto.base import DTO
from anamnesis.application.dto.views.summary import SummaryView
from anamnesis.application.errors.chat import ChatNotFoundError, SummaryNotFoundError
from anamnesis.application.interfaces.common.interactor import Interactor
from anamnesis.application.interfaces.repositories.chat import IChatRepository
from anamnesis.application.services.rendering import ViewRenderer
from anamnesis.domain.entities.chat import Chat, ChatId


class GetSummaryRequest(DTO):
    chat_id: ChatId


class GetSummaryResponse(DTO):
    summary: SummaryView


class GetSummary(Interactor[GetSummaryRequest, GetSummaryResponse]):
    def __init__(self, *, chat_repository: IChatRepository, renderer: ViewRenderer) -> None:
        self._chat_repo: IChatRepository = chat_repository
        self._renderer: ViewRenderer = renderer

    @override
    async def execute(self, request: GetSummaryRequest) -> GetSummaryResponse:
        chat: Chat | None = await self._chat_repo.find_by_id(request.chat_id)
        if chat is None:
            raise ChatNotFoundError(value=request.chat_id)
        if chat.assessment is None:
            raise SummaryNotFoundError(value=request.chat_id)
        return GetSummaryResponse(
            summary=self._renderer.summary(
                chat.assessment, chat.facts, chat.language, chat.narrative
            ),
        )
