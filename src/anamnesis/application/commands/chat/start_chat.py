from typing import override

from anamnesis.application.dto.base import DTO
from anamnesis.application.dto.views.chat import ChatView
from anamnesis.application.errors.knowledge import UnsupportedLanguageError
from anamnesis.application.interfaces.common.clock import IClock
from anamnesis.application.interfaces.common.id_generator import IIdGenerator
from anamnesis.application.interfaces.common.interactor import Interactor
from anamnesis.application.interfaces.localization.text_catalog import ITextCatalog
from anamnesis.application.interfaces.repositories.chat import IChatRepository
from anamnesis.application.services.rendering import ViewRenderer
from anamnesis.domain.entities.chat import Chat, ChatId
from anamnesis.domain.enums.message_role import MessageRole
from anamnesis.domain.types import LanguageCode


class StartChatRequest(DTO):
    consent: bool
    language: LanguageCode


class StartChatResponse(DTO):
    chat: ChatView
    message: str


class StartChat(Interactor[StartChatRequest, StartChatResponse]):
    def __init__(
        self,
        *,
        chat_repository: IChatRepository,
        catalog: ITextCatalog,
        renderer: ViewRenderer,
        id_generator: IIdGenerator[ChatId],
        clock: IClock,
    ) -> None:
        self._chat_repo: IChatRepository = chat_repository
        self._catalog: ITextCatalog = catalog
        self._renderer: ViewRenderer = renderer
        self._id_gen: IIdGenerator[ChatId] = id_generator
        self._clock: IClock = clock

    @override
    async def execute(self, request: StartChatRequest) -> StartChatResponse:
        self._validate_language(request.language)
        chat: Chat = Chat.start(
            chat_id=self._id_gen.generate(),
            consent=request.consent,
            language=request.language,
            now=self._clock.now(),
        )
        greeting: str = self._catalog.greeting(chat.language)
        chat.record(MessageRole.ASSISTANT, greeting)
        await self._chat_repo.save(chat)
        return StartChatResponse(chat=self._renderer.chat(chat), message=greeting)

    def _validate_language(self, language: LanguageCode) -> None:
        if not self._catalog.supports(language):
            raise UnsupportedLanguageError(language=language)
