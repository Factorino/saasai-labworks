from typing import TYPE_CHECKING

from anamnesis.application.dto.views.reply import ReplyView
from anamnesis.application.interfaces.reasoning.case_reasoner import ICaseReasoner
from anamnesis.application.services.rendering import ViewRenderer
from anamnesis.domain.entities.chat import Chat
from anamnesis.domain.enums.message_role import MessageRole
from anamnesis.domain.services.assessment import AssessmentService
from anamnesis.domain.services.questionnaire import Questionnaire
from anamnesis.domain.value_objects.question import Question


if TYPE_CHECKING:
    from anamnesis.application.dto.views.question import QuestionView
    from anamnesis.domain.value_objects.assessment import Assessment
    from anamnesis.domain.value_objects.inference import InferenceResult


class DialogueService:
    """Ход диалога после реплики: следующий вопрос или итог по выводу."""

    def __init__(
        self,
        *,
        questionnaire: Questionnaire,
        assessment_service: AssessmentService,
        reasoner: ICaseReasoner,
        renderer: ViewRenderer,
    ) -> None:
        self._questionnaire: Questionnaire = questionnaire
        self._assessment_service: AssessmentService = assessment_service
        self._reasoner: ICaseReasoner = reasoner
        self._renderer: ViewRenderer = renderer

    @property
    def questionnaire(self) -> Questionnaire:
        return self._questionnaire

    async def advance(self, chat: Chat) -> ReplyView:
        """Задаёт следующий вопрос; если вопросов нет или это кризис — подводит итог."""
        if not chat.is_crisis:
            question: Question | None = chat.next_question(self._questionnaire)
            if question is not None:
                return self._ask(chat, question)
        return await self._conclude(chat)

    async def _conclude(self, chat: Chat) -> ReplyView:
        """Запускает вывод; вместо сводки может прийти повторный вопрос."""
        inference: InferenceResult = await self._reasoner.infer(chat.facts)
        result: Question | Assessment = chat.conclude(
            inference, self._assessment_service, self._questionnaire
        )
        if isinstance(result, Question):
            return self._ask(chat, result)
        return ReplyView(
            stage=chat.stage,
            summary=self._renderer.summary(result, chat.facts, chat.language),
        )

    def _ask(self, chat: Chat, question: Question) -> ReplyView:
        """Записывает вопрос в историю на языке чата и отдаёт его клиенту."""
        view: QuestionView = self._renderer.question(question, chat.language)
        chat.record(MessageRole.ASSISTANT, view.text)
        return ReplyView(stage=chat.stage, question=view)
