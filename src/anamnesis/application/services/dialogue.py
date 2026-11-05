from typing import TYPE_CHECKING

from anamnesis.application.dto.views.reply import ReplyView
from anamnesis.application.interfaces.localization.text_catalog import ITextCatalog
from anamnesis.application.interfaces.reasoning.case_reasoner import ICaseReasoner
from anamnesis.application.services.rendering import ViewRenderer
from anamnesis.domain.entities.chat import Chat
from anamnesis.domain.enums.message_role import MessageRole
from anamnesis.domain.enums.referral import Referral
from anamnesis.domain.enums.urgency_level import UrgencyLevel
from anamnesis.domain.services.assessment import AssessmentService
from anamnesis.domain.services.questionnaire import Questionnaire
from anamnesis.domain.value_objects.inference import InferenceResult
from anamnesis.domain.value_objects.question import Question


if TYPE_CHECKING:
    from anamnesis.application.dto.views.question import QuestionView
    from anamnesis.domain.value_objects.assessment import Assessment


class DialogueService:
    """Ход диалога после реплики: следующий вопрос или итог по выводу."""

    def __init__(
        self,
        *,
        questionnaire: Questionnaire,
        assessment_service: AssessmentService,
        reasoner: ICaseReasoner,
        catalog: ITextCatalog,
        renderer: ViewRenderer,
    ) -> None:
        self._questionnaire: Questionnaire = questionnaire
        self._assessment_service: AssessmentService = assessment_service
        self._reasoner: ICaseReasoner = reasoner
        self._catalog: ITextCatalog = catalog
        self._renderer: ViewRenderer = renderer

    @property
    def questionnaire(self) -> Questionnaire:
        return self._questionnaire

    async def after_story(self, chat: Chat) -> ReplyView:
        """Проверяет рассказ на риск, затем продолжает диалог.

        Пока известен только рассказ, L3 может дать лишь правило по `RiskMarker`,
        поэтому такой уровень переводит чат в кризис. Направление на скорую
        тоже не ждёт уточняющих вопросов: диалог завершается со сводкой.
        """
        if chat.is_crisis:
            return await self.conclude(chat)
        inference: InferenceResult = await self._reasoner.infer(chat.facts)
        if UrgencyLevel.L3 in inference.levels:
            chat.mark_crisis()
        elif Referral.EMERGENCY_MEDICAL_CARE in inference.referrals:
            chat.finish()
        else:
            return await self.advance(chat)
        return self._summarize(chat, inference)

    async def advance(self, chat: Chat) -> ReplyView:
        """Задаёт следующий вопрос; если вопросов нет или это кризис — подводит итог."""
        if not chat.is_crisis:
            question: Question | None = chat.next_question(self._questionnaire)
            if question is not None:
                return self._ask(chat, question)
        return await self.conclude(chat)

    async def conclude(self, chat: Chat) -> ReplyView:
        """Запускает вывод; вместо сводки может прийти повторный вопрос."""
        inference: InferenceResult = await self._reasoner.infer(chat.facts)
        return self._summarize(chat, inference)

    def _summarize(self, chat: Chat, inference: InferenceResult) -> ReplyView:
        """Итог по готовому выводу; вместо сводки может прийти повторный вопрос.

        В кризисе к сводке добавляется фиксированное кризисное сообщение.
        """
        result: Question | Assessment = chat.conclude(
            inference, self._assessment_service, self._questionnaire
        )
        if isinstance(result, Question):
            return self._ask(chat, result)
        return ReplyView(
            stage=chat.stage,
            message=self._catalog.crisis_message(chat.language) if chat.is_crisis else None,
            summary=self._renderer.summary(result, chat.facts, chat.language),
        )

    def _ask(self, chat: Chat, question: Question) -> ReplyView:
        """Записывает вопрос в историю на языке чата и отдаёт его клиенту."""
        view: QuestionView = self._renderer.question(question, chat.language)
        chat.record(MessageRole.ASSISTANT, view.text)
        return ReplyView(stage=chat.stage, question=view)
