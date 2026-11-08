from collections.abc import Callable, Iterable
import json
import logging
from typing import Any, Final

from anamnesis.application.dto.base import DTO
from anamnesis.application.dto.generation import AnswerReply, NarrativeReply
from anamnesis.application.dto.views.summary import CaseView, SummaryView
from anamnesis.application.errors.llm import (
    LanguageModelReplyError,
    LanguageModelUnavailableError,
)
from anamnesis.application.interfaces.llm.instructions import IInstructions, Instruction
from anamnesis.application.interfaces.llm.language_model import ILanguageModel, ModelRequest
from anamnesis.application.interfaces.safety.reply_guard import IReplyGuard
from anamnesis.domain.enums.message_role import MessageRole
from anamnesis.domain.enums.urgency_level import UrgencyLevel
from anamnesis.domain.errors.common import ValidationError
from anamnesis.domain.types import LanguageCode
from anamnesis.domain.value_objects.message import Message
from anamnesis.domain.value_objects.narrative import Narrative
from anamnesis.domain.value_objects.reply_violation import ReplyViolation


_logger: Final[logging.Logger] = logging.getLogger(__name__)

_ATTEMPTS: Final[int] = 2
"""Первый ответ и одна перегенерация при нарушении."""


class TextGeneration:
    """Тексты языковой модели по уже вычисленным результатам.

    Модель получает уровень, его объяснение и сведения, сама она ничего не
    решает. Каждый ответ проверяется словарём недопустимого содержания. При
    нарушении ответ перегенерируется один раз, затем возвращается `None`, и
    вызывающий показывает безопасный шаблон. То же при недоступности модели.
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

    async def narrative(self, summary: SummaryView, language: LanguageCode) -> Narrative | None:
        """Описание состояния и запрос к специалисту или `None`."""
        reply: NarrativeReply | None = await self._generate(
            Instruction.SUMMARY,
            _summary_data(summary, language),
            NarrativeReply,
            texts=lambda item: (item.description, item.request),
            level=summary.level,
            language=language,
        )
        if reply is None:
            return None
        try:
            return Narrative(description=reply.description, request=reply.request)
        except ValidationError as error:
            _logger.warning("Generation ignores an invalid narrative: %s", error)
            return None

    async def reply(
        self,
        summary: SummaryView,
        messages: tuple[Message, ...],
        language: LanguageCode,
    ) -> str | None:
        """Ответ на реплику после сводки или `None`; последняя реплика — вопрос."""
        data: dict[str, Any] = {
            "language": language,
            "summary": _summary_data(summary, language),
            "history": [{"role": message.role, "text": message.text} for message in messages[:-1]],
            "message": messages[-1].text,
        }
        reply: AnswerReply | None = await self._generate(
            Instruction.REPLY,
            data,
            AnswerReply,
            texts=lambda item: (item.text,),
            level=summary.level,
            language=language,
        )
        return reply.text.strip() or None if reply is not None else None

    async def _generate[OutputT: DTO](
        self,
        task: Instruction,
        data: dict[str, Any],
        output: type[OutputT],
        *,
        texts: Callable[[OutputT], Iterable[str]],
        level: UrgencyLevel | None,
        language: LanguageCode,
    ) -> OutputT | None:
        """Ответ, прошедший проверку, или `None`."""
        instruction: str = self._instructions.text(task)
        content: str = json.dumps(data, ensure_ascii=False)
        for _ in range(_ATTEMPTS):
            reply: OutputT | None = await self._ask(instruction, content, output)
            if reply is None:
                return None
            violations: list[ReplyViolation] = await self._violations(
                texts(reply), language, level
            )
            if not violations:
                return reply
            _logger.warning("Generation rejected a reply: %s", violations)
            instruction = self._corrected(task, violations)
        return None

    async def _ask[OutputT: DTO](
        self,
        instruction: str,
        content: str,
        output: type[OutputT],
    ) -> OutputT | None:
        request = ModelRequest(
            instruction=instruction,
            messages=(Message(role=MessageRole.USER, text=content),),
        )
        try:
            return await self._model.complete_structured(request, output)
        except (LanguageModelUnavailableError, LanguageModelReplyError) as error:
            _logger.warning("Generation falls back to a template: %s", error)
            return None

    async def _violations(
        self,
        texts: Iterable[str],
        language: LanguageCode,
        level: UrgencyLevel | None,
    ) -> list[ReplyViolation]:
        found: list[ReplyViolation] = []
        for text in texts:
            found.extend(await self._guard.check(text, language, level))
        return found

    def _corrected(self, task: Instruction, violations: Iterable[ReplyViolation]) -> str:
        """Инструкция задачи с указанием отклонённых фрагментов."""
        fragments: str = "; ".join(f'"{violation.quote}"' for violation in violations)
        return "\n\n".join(
            (
                self._instructions.text(task),
                f"{self._instructions.text(Instruction.CORRECTION)} {fragments}",
            ),
        )


def _summary_data(summary: SummaryView, language: LanguageCode) -> dict[str, Any]:
    """Результаты вывода и сведения для модели: только то, что описывает состояние."""
    case: CaseView = summary.case
    return {
        "language": language,
        "urgency": summary.phrase,
        "reasons": [rule.explanation for rule in summary.explanation],
        "manifestations": [
            {"name": item.name, "quote": item.quote} for item in case.manifestations
        ],
        "stressors": [{"name": item.name, "quote": item.quote} for item in case.stressors],
        "other": list(case.unrecognized),
        "duration_weeks": case.duration_weeks,
        "frequency": case.frequency.name.lower() if case.frequency is not None else None,
        "impact": case.impact.name.lower() if case.impact is not None else None,
        "affected_domains": [item.name for item in case.affected_domains],
        "sleep": case.sleep,
        "appetite": case.appetite,
        "energy": case.energy,
        "goal": case.goal,
        "approximate": [item.fact for item in summary.approximations],
        "not_reported": list(summary.missing),
    }
