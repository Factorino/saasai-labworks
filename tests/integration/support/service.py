from collections.abc import Sequence
from typing import TYPE_CHECKING, Final

from dishka import AsyncContainer

from anamnesis.application.commands.chat.finish_chat import FinishChat, FinishChatRequest
from anamnesis.application.commands.chat.post_message import PostMessage, PostMessageRequest
from anamnesis.application.commands.chat.start_chat import StartChat, StartChatRequest
from anamnesis.application.dto.views.reply import ReplyView
from anamnesis.application.dto.views.summary import SummaryView
from anamnesis.application.interfaces.common.interactor import Interactor
from anamnesis.application.queries.assessment.assess_case import AssessCase, AssessCaseRequest
from anamnesis.application.queries.chat.get_summary import GetSummary, GetSummaryRequest
from anamnesis.domain.entities.chat import ChatId
from anamnesis.domain.types import LanguageCode, OptionCode
from tests.integration.support.cases import UserMessage


if TYPE_CHECKING:
    from anamnesis.application.commands.chat.finish_chat import FinishChatResponse
    from anamnesis.application.commands.chat.post_message import PostMessageResponse
    from anamnesis.application.commands.chat.start_chat import StartChatResponse
    from anamnesis.application.queries.assessment.assess_case import AssessCaseResponse
    from anamnesis.application.queries.chat.get_summary import GetSummaryResponse


RU: Final[LanguageCode] = LanguageCode("ru")
"""Язык всех случаев: данные пока есть только для русского."""


class Service:
    """Сценарии системы, как их вызывает API: каждый вызов — отдельный запрос."""

    def __init__(self, container: AsyncContainer) -> None:
        self._container: AsyncContainer = container

    async def start(self) -> ChatId:
        """Начинает чат с согласием на обработку данных."""
        response: StartChatResponse = await self._execute(
            StartChat, StartChatRequest(consent=True, language=RU)
        )
        return response.chat.id

    async def post(
        self,
        chat_id: ChatId,
        text: str = "",
        options: Sequence[str] = (),
    ) -> ReplyView:
        """Реплика пользователя: свой текст и/или коды выбранных вариантов."""
        request: PostMessageRequest = PostMessageRequest(
            chat_id=chat_id,
            text=text,
            option_codes=tuple(OptionCode(code) for code in options),
        )
        response: PostMessageResponse = await self._execute(PostMessage, request)
        return response.reply

    async def finish(self, chat_id: ChatId) -> ReplyView:
        """Досрочно завершает уточнение и получает сводку."""
        response: FinishChatResponse = await self._execute(
            FinishChat, FinishChatRequest(chat_id=chat_id)
        )
        return response.reply

    async def summary(self, chat_id: ChatId) -> SummaryView:
        """Сводка уже завершённого чата."""
        response: GetSummaryResponse = await self._execute(
            GetSummary, GetSummaryRequest(chat_id=chat_id)
        )
        return response.summary

    async def assess(self, request: AssessCaseRequest) -> SummaryView:
        """Сводка по сведениям о случае без диалога."""
        response: AssessCaseResponse = await self._execute(AssessCase, request)
        return response.summary

    async def converse(
        self, messages: Sequence[UserMessage], *, finish: bool = False
    ) -> ReplyView:
        """Новый чат с репликами по порядку; ответ системы на последнее действие."""
        chat_id: ChatId = await self.start()

        replies: list[ReplyView] = [
            await self.post(chat_id, message.text, message.options) for message in messages
        ]
        if finish:
            replies.append(await self.finish(chat_id))

        return replies[-1]

    async def _execute[RequestT, ResponseT](
        self,
        interactor: type[Interactor[RequestT, ResponseT]],
        request: RequestT,
    ) -> ResponseT:
        """Выполняет сценарий в контейнере запроса, как обработчик API."""
        async with self._container() as request_container:
            scenario: Interactor[RequestT, ResponseT] = await request_container.get(interactor)
            return await scenario.execute(request)
