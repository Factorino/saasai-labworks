from typing import override

from anamnesis.application.dto.base import DTO
from anamnesis.application.dto.views.reply import ReplyView
from anamnesis.application.errors.chat import ChatNotFoundError
from anamnesis.application.interfaces.common.interactor import Interactor
from anamnesis.application.interfaces.extraction.fact_extractor import IFactExtractor
from anamnesis.application.interfaces.localization.text_catalog import ITextCatalog
from anamnesis.application.interfaces.repositories.chat import IChatRepository
from anamnesis.application.services.dialogue import DialogueService
from anamnesis.application.services.rendering import ViewRenderer
from anamnesis.domain.entities.chat import Chat, ChatId
from anamnesis.domain.enums.chat_stage import ChatStage
from anamnesis.domain.enums.fact_kind import FactKind
from anamnesis.domain.enums.message_role import MessageRole
from anamnesis.domain.errors.common import ValidationError
from anamnesis.domain.types import OptionCode
from anamnesis.domain.value_objects.case_facts import CaseFacts
from anamnesis.domain.value_objects.question import Answer, Question


class PostMessageRequest(DTO):
    chat_id: ChatId
    text: str = ""
    option_codes: tuple[OptionCode, ...] = ()


class PostMessageResponse(DTO):
    reply: ReplyView


class PostMessage(Interactor[PostMessageRequest, PostMessageResponse]):
    def __init__(
        self,
        *,
        chat_repository: IChatRepository,
        extractor: IFactExtractor,
        dialogue: DialogueService,
        catalog: ITextCatalog,
        renderer: ViewRenderer,
    ) -> None:
        self._chat_repo: IChatRepository = chat_repository
        self._extractor: IFactExtractor = extractor
        self._dialogue: DialogueService = dialogue
        self._catalog: ITextCatalog = catalog
        self._renderer: ViewRenderer = renderer

    @override
    async def execute(self, request: PostMessageRequest) -> PostMessageResponse:
        chat: Chat | None = await self._chat_repo.find_by_id(request.chat_id)
        if chat is None:
            raise ChatNotFoundError(value=request.chat_id)

        reply: ReplyView = await self._reply(chat, request)
        await self._chat_repo.save(chat)
        return PostMessageResponse(reply=reply)

    async def _reply(self, chat: Chat, request: PostMessageRequest) -> ReplyView:
        match chat.stage:
            case ChatStage.STORY:
                return await self._tell_story(chat, request)
            case ChatStage.CLARIFYING:
                return await self._answer(chat, request)
            case ChatStage.SUMMARY | ChatStage.CRISIS:
                return self._talk(chat, request)

    async def _tell_story(self, chat: Chat, request: PostMessageRequest) -> ReplyView:
        self._validate_text(request)
        extracted: CaseFacts = await self._extractor.extract(request.text, chat.language)
        chat.tell_story(request.text, extracted)
        return await self._dialogue.advance(chat)

    async def _answer(self, chat: Chat, request: PostMessageRequest) -> ReplyView:
        answer = Answer(option_codes=request.option_codes, text=request.text or None)
        extracted: CaseFacts | None = await self._extract_manifestations(chat, answer)
        question: Question = chat.answer(answer, self._dialogue.questionnaire, extracted)
        chat.record(MessageRole.USER, self._renderer.answer(question, answer, chat.language))
        return await self._dialogue.advance(chat)

    def _talk(self, chat: Chat, request: PostMessageRequest) -> ReplyView:
        chat.post_message(request.text)
        message: str = self._catalog.reply(chat.stage, chat.language)
        chat.record(MessageRole.ASSISTANT, message)
        return ReplyView(stage=chat.stage, message=message)

    async def _extract_manifestations(self, chat: Chat, answer: Answer) -> CaseFacts | None:
        """Ищет термины только в ответе на вопрос о проявлениях."""
        pending: Question | None = chat.pending
        if answer.text is None or pending is None or pending.fact is not FactKind.MANIFESTATIONS:
            return None
        return await self._extractor.extract(answer.text, chat.language)

    @staticmethod
    def _validate_text(request: PostMessageRequest) -> None:
        if not request.text.strip():
            raise ValidationError(field="text", reason="the story must not be empty")
