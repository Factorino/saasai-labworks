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
from anamnesis.domain.enums.chat import ChatStage, MessageRole
from anamnesis.domain.enums.fact_kind import ESTIMATED_FACTS, FactKind
from anamnesis.domain.errors.chat import ChatStageError
from anamnesis.domain.errors.common import ValidationError
from anamnesis.domain.types import OptionCode
from anamnesis.domain.value_objects.case_facts import CaseFacts
from anamnesis.domain.value_objects.clarification import Answer, Question
from anamnesis.domain.value_objects.crisis_signal import CrisisSignal


_EXTRACTED_ANSWERS: Final[frozenset[FactKind]] = frozenset(
    {FactKind.MANIFESTATIONS, *ESTIMATED_FACTS},
)
"""Вопросы, из своего ответа на которые извлекаются сведения."""


class PostMessageBody(DTO):
    """Реплика пользователя: свой текст и/или коды выбранных вариантов.

    Attributes:
        text: Свой текст: рассказ, ответ своими словами или свободная реплика.
        option_codes: Коды выбранных вариантов ответа на вопрос.
    """

    text: str = ""
    option_codes: tuple[OptionCode, ...] = ()


class PostMessageRequest(PostMessageBody):
    """Реплика пользователя в чате.

    Attributes:
        chat_id: Идентификатор чата.
    """

    chat_id: ChatId


class PostMessageResponse(DTO):
    """Ответ системы на реплику.

    Attributes:
        reply: Вопрос, сводка или сообщение.
    """

    reply: ReplyView


class PostMessage(Interactor[PostMessageRequest, PostMessageResponse]):
    """Принимает реплику и продолжает диалог.

    Смысл реплики зависит от этапа: рассказ, ответ на вопрос или свободная
    реплика после сводки. Каждый текст сначала проверяет кризисный детектор;
    при кризисной находке языковая модель не вызывается.
    """

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

    @staticmethod
    def _validate_text(request: PostMessageRequest) -> None:
        if not request.text.strip():
            raise ValidationError(subject="text", reason="the story must not be empty")

    @override
    async def execute(self, request: PostMessageRequest) -> PostMessageResponse:
        chat: Chat | None = await self._chat_repo.find_by_id(request.chat_id)
        if chat is None:
            raise ChatNotFoundError(value=request.chat_id)

        reply: ReplyView = await self._reply(chat, request)

        await self._chat_repo.save(chat)

        return PostMessageResponse(reply=reply)

    async def _reply(self, chat: Chat, request: PostMessageRequest) -> ReplyView:
        """Реплика по смыслу этапа."""
        match chat.stage:
            case ChatStage.STORY:
                return await self._tell_story(chat, request)
            case ChatStage.CLARIFYING:
                return await self._answer(chat, request)
            case ChatStage.SUMMARY | ChatStage.CRISIS:
                return await self._talk(chat, request)
            case ChatStage.FINISHED:
                raise ChatStageError(action="post a message", stage=chat.stage)

    async def _tell_story(self, chat: Chat, request: PostMessageRequest) -> ReplyView:
        """Рассказ: детектор, извлечение, проверка риска и первый вопрос."""
        self._validate_text(request)

        signals: tuple[CrisisSignal, ...] = await self._detect(chat, request.text)
        extracted: CaseFacts = await self._extraction.extract(
            chat.language, request.text, with_model=not _is_crisis(signals)
        )

        chat.tell_story(request.text, extracted)
        chat.register_signals(signals)

        return await self._dialogue.after_story(chat)

    async def _answer(self, chat: Chat, request: PostMessageRequest) -> ReplyView:
        """Ответ на вопрос: детектор по своему тексту, извлечение, следующий шаг."""
        answer: Answer = Answer(option_codes=request.option_codes, text=request.text or None)

        signals: tuple[CrisisSignal, ...] = (
            await self._detect(chat, answer.text) if answer.text is not None else ()
        )
        extracted: CaseFacts | None = await self._extract(
            chat, answer, with_model=not _is_crisis(signals)
        )

        question: Question = chat.answer(answer, self._dialogue.questionnaire, extracted)
        chat.record(MessageRole.USER, self._renderer.answer(chat.language, question, answer))
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
            chat.language, answer.text, pending.fact, with_model=with_model
        )


def _is_crisis(signals: tuple[CrisisSignal, ...]) -> bool:
    """Кризисная находка: тогда языковая модель не вызывается вовсе."""
    return any(signal.category.is_crisis for signal in signals)
