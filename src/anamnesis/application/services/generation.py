from collections.abc import Callable, Iterable
from typing import Final

from anamnesis.application.dto.base import DTO
from anamnesis.application.dto.generation import (
    AnswerData,
    AnswerReply,
    HistoryData,
    NarrativeReply,
    PracticeData,
    SummaryData,
)
from anamnesis.application.dto.views.summary import SummaryView
from anamnesis.application.errors.llm import (
    LanguageModelReplyError,
    LanguageModelUnavailableError,
)
from anamnesis.application.interfaces.llm.instructions import IInstructions, Instruction
from anamnesis.application.interfaces.llm.language_model import (
    ILanguageModel,
    ModelData,
    ModelRequest,
)
from anamnesis.application.interfaces.safety.reply_guard import IReplyGuard, ReplyViolation
from anamnesis.domain.enums.recommendation import UrgencyLevel
from anamnesis.domain.errors.common import ValidationError
from anamnesis.domain.types import LanguageCode
from anamnesis.domain.value_objects.message import Message
from anamnesis.domain.value_objects.narrative import Narrative


_ATTEMPTS: Final[int] = 2
"""Первый ответ и одна перегенерация при нарушении."""

type _ReplyTexts[OutputT] = Callable[[OutputT], Iterable[str]]
"""Тексты ответа модели, которые проверяет `IReplyGuard`."""


class TextGeneration:
    """Тексты языковой модели по уже вычисленным результатам.

    Модель получает уровень, его объяснение и сведения, сама она ничего не
    решает. Каждый ответ проверяется словарём недопустимого содержания. При
    нарушении ответ перегенерируется один раз, затем возвращается `None`, и
    вызывающий показывает безопасный шаблон. То же при недоступности модели.
    Инструкции всегда фиксированы: отклонённые фрагменты передаются как данные.
    """

    def __init__(
        self,
        *,
        model: ILanguageModel,
        guard: IReplyGuard,
        instructions: IInstructions,
    ) -> None:
        self._model: ILanguageModel = model
        self._guard: IReplyGuard = guard
        self._instructions: IInstructions = instructions

    async def narrative(self, language: LanguageCode, summary: SummaryView) -> Narrative | None:
        """Описание состояния и запрос к специалисту или `None`."""
        reply: NarrativeReply | None = await self._generate(
            Instruction.SUMMARY,
            SummaryData.from_summary(language, summary),
            NarrativeReply,
            texts=lambda item: (item.description, item.request),
            level=summary.level,
            language=language,
        )
        if reply is None:
            return None

        try:
            narrative: Narrative = Narrative(description=reply.description, request=reply.request)
        except ValidationError:
            return None
        return narrative

    async def reply(
        self,
        language: LanguageCode,
        summary: SummaryView,
        messages: tuple[Message, ...],
    ) -> str | None:
        """Ответ на реплику после сводки или `None`; последняя реплика — вопрос."""
        data: AnswerData = AnswerData(
            language=language,
            summary=SummaryData.from_summary(language, summary),
            practices=tuple(PracticeData.from_practice(item) for item in summary.practices),
            history=tuple(HistoryData.from_domain(message) for message in messages[:-1]),
            message=messages[-1].text,
        )

        reply: AnswerReply | None = await self._generate(
            Instruction.REPLY,
            data,
            AnswerReply,
            texts=lambda item: (item.text,),
            level=summary.level,
            language=language,
        )
        if reply is None:
            return None

        text: str = reply.text.strip()
        return text or None

    async def _generate[OutputT: DTO](
        self,
        task: Instruction,
        data: ModelData,
        output: type[OutputT],
        *,
        texts: _ReplyTexts[OutputT],
        level: UrgencyLevel | None,
        language: LanguageCode,
    ) -> OutputT | None:
        """Ответ, прошедший проверку, или `None`."""
        request: ModelRequest = ModelRequest(instruction=self._instructions.text(task), data=data)

        for _ in range(_ATTEMPTS):
            reply: OutputT | None = await self._ask(request, output)
            if reply is None:
                return None

            violations: list[ReplyViolation] = await self._violations(
                texts(reply), language, level
            )
            if not violations:
                return reply

            request = ModelRequest(
                instruction=self._corrected(task),
                data=data,
                rejected_fragments=tuple(item.quote for item in violations),
            )

        return None

    async def _ask[OutputT: DTO](
        self,
        request: ModelRequest,
        output: type[OutputT],
    ) -> OutputT | None:
        """Ответ модели или `None`, если она недоступна или ответила не по схеме."""
        try:
            reply: OutputT = await self._model.complete_structured(request, output)
        except (LanguageModelUnavailableError, LanguageModelReplyError):
            return None
        return reply

    async def _violations(
        self,
        texts: Iterable[str],
        language: LanguageCode,
        level: UrgencyLevel | None,
    ) -> list[ReplyViolation]:
        """Нарушения во всех текстах ответа."""
        found: list[ReplyViolation] = []
        for text in texts:
            found.extend(await self._guard.check(text, language, level))
        return found

    def _corrected(self, task: Instruction) -> str:
        """Инструкция задачи с дополнением об исправлении отклонённых фрагментов."""
        return "\n\n".join(
            (self._instructions.text(task), self._instructions.text(Instruction.CORRECTION)),
        )
