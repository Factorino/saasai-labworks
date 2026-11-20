from typing import override

from anamnesis.application.dto.base import DTO
from anamnesis.application.dto.views.chat import ChatView
from anamnesis.application.interfaces.common.clock import IClock
from anamnesis.application.interfaces.common.id_generator import IIdGenerator
from anamnesis.application.interfaces.common.interactor import Interactor
from anamnesis.application.interfaces.localization.dialogue_texts import IDialogueTexts
from anamnesis.application.interfaces.repositories.chat import IChatRepository
from anamnesis.application.services.languages import SupportedLanguages
from anamnesis.domain.entities.chat import Chat, ChatId
from anamnesis.domain.enums.chat import MessageRole
from anamnesis.domain.types import LanguageCode


class StartChatRequest(DTO):
    """Начало диалога.

    Attributes:
        consent: Согласие на обработку данных.
        language: Язык диалога.
    """

    consent: bool
    language: LanguageCode


class StartChatResponse(DTO):
    """Начатый чат и приветствие.

    Attributes:
        chat: Чат.
        message: Приглашение рассказать, что беспокоит.
    """

    chat: ChatView
    message: str


class StartChat(Interactor[StartChatRequest, StartChatResponse]):
    """Начинает диалог: проверяет язык и согласие, здоровается."""

    def __init__(
        self,
        *,
        chat_repository: IChatRepository,
        languages: SupportedLanguages,
        dialogue_texts: IDialogueTexts,
        id_generator: IIdGenerator[ChatId],
        clock: IClock,
    ) -> None:
        self._chat_repo: IChatRepository = chat_repository
        self._languages: SupportedLanguages = languages
        self._dialogue_texts: IDialogueTexts = dialogue_texts
        self._id_gen: IIdGenerator[ChatId] = id_generator
        self._clock: IClock = clock

    @override
    async def execute(self, request: StartChatRequest) -> StartChatResponse:
        self._languages.validate(request.language)

        chat: Chat = Chat.start(
            chat_id=self._id_gen.generate(),
            consent=request.consent,
            language=request.language,
            now=self._clock.now(),
        )
        greeting: str = self._dialogue_texts.greeting(chat.language)
        chat.record(MessageRole.ASSISTANT, greeting)

        await self._chat_repo.save(chat)

        response: StartChatResponse = StartChatResponse(
            chat=ChatView.from_domain(chat),
            message=greeting,
        )
        return response
