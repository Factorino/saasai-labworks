from typing import TYPE_CHECKING

from anamnesis.application.dto.views.reply import ReplyView
from anamnesis.application.interfaces.localization.dialogue_texts import IDialogueTexts
from anamnesis.application.interfaces.reasoning.case_reasoner import ICaseReasoner
from anamnesis.application.services.generation import TextGeneration
from anamnesis.application.services.rendering import ViewRenderer
from anamnesis.domain.entities.chat import Chat
from anamnesis.domain.enums.chat import ChatStage, MessageRole
from anamnesis.domain.enums.recommendation import Referral, UrgencyLevel
from anamnesis.domain.services.assessment import AssessmentService
from anamnesis.domain.services.questionnaire import Questionnaire
from anamnesis.domain.value_objects.assessment import Assessment
from anamnesis.domain.value_objects.clarification import Question
from anamnesis.domain.value_objects.inference import InferenceResult
from anamnesis.domain.value_objects.narrative import Narrative


if TYPE_CHECKING:
    from anamnesis.application.dto.views.question import QuestionView
    from anamnesis.application.dto.views.summary import SummaryView


class DialogueService:
    """Ход диалога после реплики: следующий вопрос или итог по выводу."""

    def __init__(
        self,
        *,
        questionnaire: Questionnaire,
        assessment_service: AssessmentService,
        reasoner: ICaseReasoner,
        dialogue_texts: IDialogueTexts,
        renderer: ViewRenderer,
        generation: TextGeneration,
    ) -> None:
        self._questionnaire: Questionnaire = questionnaire
        self._assessment_service: AssessmentService = assessment_service
        self._reasoner: ICaseReasoner = reasoner
        self._dialogue_texts: IDialogueTexts = dialogue_texts
        self._renderer: ViewRenderer = renderer
        self._generation: TextGeneration = generation

    @property
    def questionnaire(self) -> Questionnaire:
        """Опросник: нужен чату, чтобы принять ответ."""
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

        return await self._summarize(chat, inference)

    async def advance(self, chat: Chat) -> ReplyView:
        """Задаёт следующий вопрос; если вопросов нет, диалог завершён или кризис — итог."""
        if chat.stage is ChatStage.CLARIFYING:
            question: Question | None = chat.next_question(self._questionnaire)
            if question is not None:
                return self._ask(chat, question)

        return await self.conclude(chat)

    async def conclude(self, chat: Chat) -> ReplyView:
        """Запускает вывод; вместо сводки может прийти повторный вопрос."""
        inference: InferenceResult = await self._reasoner.infer(chat.facts)
        return await self._summarize(chat, inference)

    async def talk(self, chat: Chat) -> ReplyView:
        """Отвечает на реплику после сводки; в кризисе — только фиксированным шаблоном."""
        message: str = await self._generated_reply(chat) or self._dialogue_texts.reply(
            chat.language, chat.stage
        )
        chat.record(MessageRole.ASSISTANT, message)

        reply: ReplyView = ReplyView(stage=chat.stage, message=message)
        return reply

    async def _summarize(self, chat: Chat, inference: InferenceResult) -> ReplyView:
        """Итог по готовому выводу; вместо сводки может прийти повторный вопрос.

        В кризисе к сводке добавляется фиксированное кризисное сообщение.
        """
        result: Question | Assessment = chat.conclude(
            inference, self._assessment_service, self._questionnaire
        )
        if isinstance(result, Question):
            return self._ask(chat, result)

        chat.describe(await self._generated_narrative(chat, result))

        reply: ReplyView = ReplyView(
            stage=chat.stage,
            message=self._dialogue_texts.crisis_message(chat.language) if chat.is_crisis else None,
            summary=self._renderer.summary(chat.language, result, chat.facts, chat.narrative),
        )
        return reply

    async def _generated_narrative(
        self,
        chat: Chat,
        assessment: Assessment,
    ) -> Narrative | None:
        """Текст сводки от модели; при риске он не генерируется, остаётся шаблон."""
        if _is_sensitive(assessment):
            return None

        draft: SummaryView = self._renderer.summary(chat.language, assessment, chat.facts)
        return await self._generation.narrative(chat.language, draft)

    async def _generated_reply(self, chat: Chat) -> str | None:
        """Ответ модели на реплику после сводки; при риске и в кризисе — `None`."""
        if chat.assessment is None or _is_sensitive(chat.assessment):
            return None

        summary: SummaryView = self._renderer.summary(
            chat.language, chat.assessment, chat.facts, chat.narrative
        )
        return await self._generation.reply(chat.language, summary, chat.messages)

    def _ask(self, chat: Chat, question: Question) -> ReplyView:
        """Записывает вопрос в историю на языке чата и отдаёт его клиенту."""
        view: QuestionView = self._renderer.question(chat.language, question)
        chat.record(MessageRole.ASSISTANT, view.text)

        reply: ReplyView = ReplyView(stage=chat.stage, question=view)
        return reply


def _is_sensitive(assessment: Assessment) -> bool:
    """Кризис, L3 или признаки самоповреждения: языковая модель текст не пишет."""
    return Referral.CRISIS_HELPLINE in assessment.referrals
