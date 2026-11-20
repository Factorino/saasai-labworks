from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Final, cast

from dishka import AsyncContainer

from anamnesis.application.commands.chat.post_message import PostMessage, PostMessageRequest
from anamnesis.application.commands.chat.start_chat import StartChat, StartChatRequest
from anamnesis.application.dto.base import DTO
from anamnesis.application.dto.extraction import ExtractionReply
from anamnesis.application.dto.views.question import QuestionView
from anamnesis.application.dto.views.summary import SummaryView
from anamnesis.application.errors.llm import (
    LanguageModelReplyError,
    LanguageModelUnavailableError,
)
from anamnesis.application.interfaces.llm.language_model import ILanguageModel, ModelRequest
from anamnesis.application.queries.assessment.assess_case import AssessCase, AssessCaseRequest
from anamnesis.domain.entities.chat import ChatId
from anamnesis.domain.enums.fact_kind import FactKind
from anamnesis.domain.enums.recommendation import UrgencyLevel
from anamnesis.domain.types import LanguageCode, OptionCode
from anamnesis.domain.value_objects.clarification import REFUSE_OPTION_CODE
from benchmarks.utils.support import load_data


if TYPE_CHECKING:
    from anamnesis.application.dto.views.chat import ChatView
    from anamnesis.application.dto.views.reply import ReplyView


_RU: Final[LanguageCode] = LanguageCode("ru")


@dataclass(frozen=True, slots=True)
class Appeal:
    """Синтетическое обращение с ответами и эталонными фактами."""

    id: str
    story: str
    answers: dict[str, str]
    self_harm: str
    manifestations: list[str]
    stressors: list[str]
    optional: list[str]
    duration_weeks: int
    frequency: int
    impact: int
    level: str


@dataclass(frozen=True, slots=True)
class Evaluation:
    """Сводка после диалога и срочность по эталонным фактам."""

    appeal: Appeal
    summary: SummaryView
    reference_level: UrgencyLevel | None


def load_appeals() -> list[Appeal]:
    """Загрузить размеченные обращения."""
    rows: list[dict[str, Any]] = cast("list[dict[str, Any]]", load_data("appeals.yaml"))
    return [Appeal(**row) for row in rows]


def answer(chat_id: ChatId, question: QuestionView, appeal: Appeal) -> PostMessageRequest:
    """Подготовить ответ по разметке или пропустить вопрос."""
    if question.fact is FactKind.SELF_HARM:
        return PostMessageRequest(chat_id=chat_id, option_codes=(OptionCode(appeal.self_harm),))

    text: str | None = appeal.answers.get(question.fact.value)
    if text is not None:
        return PostMessageRequest(chat_id=chat_id, text=text)
    return PostMessageRequest(chat_id=chat_id, option_codes=(REFUSE_OPTION_CODE,))


async def evaluate(scope: AsyncContainer, appeal: Appeal) -> Evaluation:
    """Сравнить оценку после диалога с оценкой по фактам из разметки."""
    start: StartChat = await scope.get(StartChat)
    post: PostMessage = await scope.get(PostMessage)
    assess: AssessCase = await scope.get(AssessCase)

    chat: ChatView = (await start.execute(StartChatRequest(consent=True, language=_RU))).chat
    story: PostMessageRequest = PostMessageRequest(chat_id=chat.id, text=appeal.story)
    reply: ReplyView = (await post.execute(story)).reply
    while reply.question is not None:
        reply = (await post.execute(answer(chat.id, reply.question, appeal))).reply
    if reply.summary is None:
        raise RuntimeError(f"Обращение {appeal.id} завершилось без сводки")

    reference: AssessCaseRequest = AssessCaseRequest.model_validate(
        {
            "language": _RU,
            "manifestations": appeal.manifestations,
            "stressors": appeal.stressors,
            "duration_weeks": appeal.duration_weeks,
            "frequency": appeal.frequency,
            "impact": appeal.impact,
            "self_harm": appeal.self_harm,
        }
    )
    reference_level: UrgencyLevel | None = (await assess.execute(reference)).summary.level
    return Evaluation(appeal=appeal, summary=reply.summary, reference_level=reference_level)


@dataclass(slots=True)
class ModelCalls:
    """Декоратор языковой модели со счётчиками извлечения."""

    model: ILanguageModel
    extractions: int = 0
    invalid_extractions: int = 0

    async def complete_structured[OutputT: DTO](
        self,
        request: ModelRequest,
        output: type[OutputT],
    ) -> OutputT:
        """Посчитать запросы на извлечение и ответы вне схемы."""
        extraction: bool = issubclass(output, ExtractionReply)
        if extraction:
            self.extractions += 1
        try:
            return await self.model.complete_structured(request, output)
        except LanguageModelReplyError:
            if extraction:
                self.invalid_extractions += 1
            raise
        except LanguageModelUnavailableError as error:
            raise RuntimeError("Для измерения нужна доступная языковая модель") from error


def count_calls(model: ILanguageModel) -> ILanguageModel:
    """Подключить счётчик как декоратор языковой модели."""
    return ModelCalls(model)
