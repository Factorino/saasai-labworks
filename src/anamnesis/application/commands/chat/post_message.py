from typing import Final, override

from anamnesis.application.dto.base import DTO
from anamnesis.application.dto.views.reply import ReplyView
from anamnesis.application.errors.chat import ChatNotFoundError
from anamnesis.application.interfaces.common.interactor import Interactor
from anamnesis.application.interfaces.repositories.chat import IChatRepository
from anamnesis.application.interfaces.safety.crisis_detector import ICrisisDetector
from anamnesis.application.services.dialogue import DialogueService
from anamnesis.application.services.extraction import FactExtraction
from anamnesis.application.services.rendering import ViewRenderer
from anamnesis.domain.entities.chat import Chat, ChatId
from anamnesis.domain.enums.chat_stage import ChatStage
from anamnesis.domain.enums.fact_kind import ESTIMATED_FACTS, FactKind
from anamnesis.domain.enums.message_role import MessageRole
from anamnesis.domain.errors.common import ValidationError
from anamnesis.domain.types import OptionCode
from anamnesis.domain.value_objects.case_facts import CaseFacts
from anamnesis.domain.value_objects.crisis_signal import CrisisSignal
from anamnesis.domain.value_objects.question import Answer, Question


_EXTRACTED_ANSWERS: Final[frozenset[FactKind]] = frozenset(
    {FactKind.MANIFESTATIONS, *ESTIMATED_FACTS},
)
"""Вопросы, из своего ответа на которые извлекаются сведения."""


class PostMessageBody(DTO):
    """Реплика пользователя: свой текст и/или коды выбранных вариантов."""

    text: str = ""
    option_codes: tuple[OptionCode, ...] = ()


class PostMessageRequest(PostMessageBody):
    chat_id: ChatId


class PostMessageResponse(DTO):
    reply: ReplyView


class PostMessage(Interactor[PostMessageRequest, PostMessageResponse]):
    def __init__(
        self,
        *,
        chat_repository: IChatRepository,
        extraction: FactExtraction,
        detector: ICrisisDetector,
        dialogue: DialogueService,
        renderer: ViewRenderer,
    ) -> None:
        self._chat_repo: IChatRepository = chat_repository
        self._extraction: FactExtraction = extraction
        self._detector: ICrisisDetector = detector
        self._dialogue: DialogueService = dialogue
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
                return await self._talk(chat, request)

    async def _tell_story(self, chat: Chat, request: PostMessageRequest) -> ReplyView:
        self._validate_text(request)
        signals: tuple[CrisisSignal, ...] = await self._detect(chat, request.text)
        extracted: CaseFacts = await self._extraction.extract(
            request.text, chat.language, with_model=not _is_crisis(signals)
        )
        chat.tell_story(request.text, extracted)
        chat.register_signals(signals)
        return await self._dialogue.after_story(chat)

    async def _answer(self, chat: Chat, request: PostMessageRequest) -> ReplyView:
        answer = Answer(option_codes=request.option_codes, text=request.text or None)
        signals: tuple[CrisisSignal, ...] = (
            await self._detect(chat, answer.text) if answer.text is not None else ()
        )
        extracted: CaseFacts | None = await self._extract(
            chat, answer, with_model=not _is_crisis(signals)
        )
        question: Question = chat.answer(answer, self._dialogue.questionnaire, extracted)
        chat.record(MessageRole.USER, self._renderer.answer(question, answer, chat.language))
        chat.register_signals(signals)
        return await self._dialogue.advance(chat)

    async def _talk(self, chat: Chat, request: PostMessageRequest) -> ReplyView:
        """Свободная реплика: ответ по сводке, а при новом кризисе — кризисная сводка."""
        was_crisis: bool = chat.is_crisis
        chat.post_message(request.text)
        chat.register_signals(await self._detect(chat, request.text))
        if chat.is_crisis and not was_crisis:
            return await self._dialogue.conclude(chat)
        return await self._dialogue.talk(chat)

    async def _detect(self, chat: Chat, text: str) -> tuple[CrisisSignal, ...]:
        """Находки кризисного детектора; проверка идёт до языковой модели."""
        return await self._detector.detect(text, chat.language)

    async def _extract(self, chat: Chat, answer: Answer, *, with_model: bool) -> CaseFacts | None:
        """Сведения из своего текста ответа о проявлениях, длительности, частоте или влиянии."""
        pending: Question | None = chat.pending
        if answer.text is None or pending is None or pending.fact not in _EXTRACTED_ANSWERS:
            return None
        return await self._extraction.extract(
            answer.text, chat.language, pending.fact, with_model=with_model
        )

    @staticmethod
    def _validate_text(request: PostMessageRequest) -> None:
        if not request.text.strip():
            raise ValidationError(field="text", reason="the story must not be empty")


def _is_crisis(signals: tuple[CrisisSignal, ...]) -> bool:
    """Кризисная находка: тогда языковая модель не вызывается вовсе."""
    return any(signal.category.is_crisis for signal in signals)
