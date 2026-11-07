from typing import TYPE_CHECKING, override

from anamnesis.application.dto.base import DTO
from anamnesis.application.dto.views.reply import ReplyView
from anamnesis.application.errors.chat import ChatNotFoundError
from anamnesis.application.interfaces.common.interactor import Interactor
from anamnesis.application.interfaces.extraction.estimate_extractor import IEstimateExtractor
from anamnesis.application.interfaces.extraction.fact_extractor import IFactExtractor
from anamnesis.application.interfaces.extraction.fact_normalizer import IFactNormalizer
from anamnesis.application.interfaces.localization.text_catalog import ITextCatalog
from anamnesis.application.interfaces.repositories.chat import IChatRepository
from anamnesis.application.interfaces.safety.crisis_detector import ICrisisDetector
from anamnesis.application.services.dialogue import DialogueService
from anamnesis.application.services.rendering import ViewRenderer
from anamnesis.domain.entities.chat import Chat, ChatId
from anamnesis.domain.enums.chat_stage import ChatStage
from anamnesis.domain.enums.fact_kind import ESTIMATED_FACTS, FactKind
from anamnesis.domain.enums.message_role import MessageRole
from anamnesis.domain.errors.common import ValidationError
from anamnesis.domain.types import OptionCode
from anamnesis.domain.value_objects.case_facts import CaseFacts
from anamnesis.domain.value_objects.question import Answer, Question


if TYPE_CHECKING:
    from anamnesis.application.dto.estimate import Estimate


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
        extractor: IFactExtractor,
        estimator: IEstimateExtractor,
        normalizer: IFactNormalizer,
        detector: ICrisisDetector,
        dialogue: DialogueService,
        catalog: ITextCatalog,
        renderer: ViewRenderer,
    ) -> None:
        self._chat_repo: IChatRepository = chat_repository
        self._extractor: IFactExtractor = extractor
        self._estimator: IEstimateExtractor = estimator
        self._normalizer: IFactNormalizer = normalizer
        self._detector: ICrisisDetector = detector
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
                return await self._talk(chat, request)

    async def _tell_story(self, chat: Chat, request: PostMessageRequest) -> ReplyView:
        self._validate_text(request)
        extracted: CaseFacts = await self._extractor.extract(request.text, chat.language)
        chat.tell_story(request.text, extracted)
        await self._screen(chat, request.text)
        return await self._dialogue.after_story(chat)

    async def _answer(self, chat: Chat, request: PostMessageRequest) -> ReplyView:
        answer = Answer(option_codes=request.option_codes, text=request.text or None)
        extracted: CaseFacts | None = await self._extract(chat, answer)
        question: Question = chat.answer(answer, self._dialogue.questionnaire, extracted)
        chat.record(MessageRole.USER, self._renderer.answer(question, answer, chat.language))
        if answer.text is not None:
            await self._screen(chat, answer.text)
        return await self._dialogue.advance(chat)

    async def _talk(self, chat: Chat, request: PostMessageRequest) -> ReplyView:
        """Свободная реплика: шаблонный ответ, а при новом кризисе — кризисная сводка."""
        was_crisis: bool = chat.is_crisis
        chat.post_message(request.text)
        await self._screen(chat, request.text)
        if chat.is_crisis and not was_crisis:
            return await self._dialogue.conclude(chat)
        message: str = self._catalog.reply(chat.stage, chat.language)
        chat.record(MessageRole.ASSISTANT, message)
        return ReplyView(stage=chat.stage, message=message)

    async def _screen(self, chat: Chat, text: str) -> None:
        """Проверяет реплику кризисным детектором; кризисная находка переводит чат в кризис."""
        chat.register_signals(await self._detector.detect(text, chat.language))

    async def _extract(self, chat: Chat, answer: Answer) -> CaseFacts | None:
        """Сведения из своего текста ответа.

        В ответе о проявлениях ищутся термины, в ответе о длительности,
        частоте или влиянии — оценка, которая затем нормализуется.
        """
        pending: Question | None = chat.pending
        if answer.text is None or pending is None:
            return None
        if pending.fact is FactKind.MANIFESTATIONS:
            return await self._extractor.extract(answer.text, chat.language)
        if pending.fact in ESTIMATED_FACTS:
            estimate: Estimate | None = await self._estimator.extract(
                answer.text, pending.fact, chat.language
            )
            return self._normalizer.normalize(estimate) if estimate is not None else None
        return None

    @staticmethod
    def _validate_text(request: PostMessageRequest) -> None:
        if not request.text.strip():
            raise ValidationError(field="text", reason="the story must not be empty")
