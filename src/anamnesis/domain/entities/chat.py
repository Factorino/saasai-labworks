from dataclasses import field
from datetime import datetime
from typing import ClassVar, NewType, Self, cast
from uuid import UUID

from anamnesis.domain.entities.base import Entity, entity
from anamnesis.domain.enums.chat_stage import ChatStage
from anamnesis.domain.enums.fact_kind import FactKind
from anamnesis.domain.enums.message_role import MessageRole
from anamnesis.domain.enums.referral import Referral
from anamnesis.domain.enums.self_harm_screening import SelfHarmScreening
from anamnesis.domain.errors.chat import ChatStageError, ConsentRequiredError
from anamnesis.domain.services.assessment import AssessmentService
from anamnesis.domain.services.questionnaire import Questionnaire
from anamnesis.domain.types import LanguageCode
from anamnesis.domain.value_objects.assessment import Assessment
from anamnesis.domain.value_objects.case_facts import CaseFacts
from anamnesis.domain.value_objects.crisis_signal import CrisisSignal
from anamnesis.domain.value_objects.inference import InferenceResult
from anamnesis.domain.value_objects.message import Message
from anamnesis.domain.value_objects.question import Answer, Question


ChatId = NewType("ChatId", UUID)
"""Идентификатор чата."""


@entity
class Chat(Entity[ChatId]):
    """Диалог с одним пользователем.

    Attributes:
        language: Язык диалога: по нему извлекаются термины и подбираются тексты.
        created_at: Когда начат диалог.
        stage: Текущий этап.
        facts: Накопленные сведения о случае.
        asked: Какие вопросы уже заданы.
        pending: Вопрос, который ждёт ответа.
        finished: Пользователь завершил диалог досрочно.
        self_harm_followed_up: Повторный вопрос о самоповреждении уже задан.
        assessment: Выданная оценка.
        messages: Последние `HISTORY_LIMIT` реплик.
        signals: Находки кризисного детектора за весь диалог.
    """

    HISTORY_LIMIT: ClassVar[int] = 20

    language: LanguageCode
    created_at: datetime
    stage: ChatStage = ChatStage.STORY
    facts: CaseFacts = field(default_factory=CaseFacts)
    asked: tuple[FactKind, ...] = ()
    pending: Question | None = None
    finished: bool = False
    self_harm_followed_up: bool = False
    assessment: Assessment | None = None
    messages: tuple[Message, ...] = ()
    signals: tuple[CrisisSignal, ...] = ()

    @classmethod
    def start(
        cls,
        *,
        chat_id: ChatId,
        consent: bool,
        language: LanguageCode,
        now: datetime,
    ) -> Self:
        """Начинает диалог."""
        cls._validate_consent(consent=consent)
        return cls(id=chat_id, language=language, created_at=now)

    @property
    def is_crisis(self) -> bool:
        """Чат в кризисном сценарии."""
        return self.stage is ChatStage.CRISIS

    def tell_story(self, text: str, extracted: CaseFacts) -> None:
        """Принимает свободный рассказ о том, что беспокоит."""
        self._validate_stage(ChatStage.STORY, action="tell the story")
        self.record(MessageRole.USER, text)
        self.facts = self.facts.absorb(text, extracted)
        self.stage = ChatStage.CLARIFYING
        self._check_crisis()

    def next_question(self, questionnaire: Questionnaire) -> Question | None:
        """Неотвеченный вопрос или следующий по опроснику."""
        self._validate_stage(ChatStage.CLARIFYING, action="ask a question")
        if self.pending is not None:
            return self.pending
        if self.finished:
            return None
        question: Question | None = questionnaire.next_question(self.facts, self.asked)
        if question is not None:
            self._ask(question)
        return question

    def answer(
        self,
        answer: Answer,
        questionnaire: Questionnaire,
        extracted: CaseFacts | None = None,
    ) -> Question:
        """Принимает ответ на вопрос и возвращает вопрос, на который ответили."""
        self._validate_stage(ChatStage.CLARIFYING, action="answer a question")
        self._validate_pending()
        question: Question = cast("Question", self.pending)
        self.facts = questionnaire.apply(self.facts, question, answer, extracted)
        self.pending = None
        self._check_crisis()
        return question

    def finish(self) -> None:
        """Завершает диалог, не дожидаясь конца вопросов."""
        self._validate_stage(ChatStage.STORY, ChatStage.CLARIFYING, action="finish the dialogue")
        self.finished = True
        self.pending = None
        self.stage = ChatStage.CLARIFYING

    def conclude(
        self,
        inference: InferenceResult,
        assessment_service: AssessmentService,
        questionnaire: Questionnaire,
    ) -> Question | Assessment:
        """Подводит итог по результату вывода."""
        self._validate_stage(ChatStage.CLARIFYING, ChatStage.CRISIS, action="conclude")
        self._validate_can_conclude(questionnaire)

        if self._needs_self_harm_follow_up(inference):
            self.self_harm_followed_up = True
            question: Question = questionnaire.self_harm_follow_up
            self._ask(question)
            return question

        self.assessment = assessment_service.assess(
            self.facts,
            inference,
            crisis=self.is_crisis,
            signals=self.signals,
        )
        if not self.is_crisis:
            self.stage = ChatStage.SUMMARY
        return self.assessment

    def register_signals(self, signals: tuple[CrisisSignal, ...]) -> None:
        """Запоминает находки детектора; кризисная переводит чат в кризис на любом этапе."""
        known: set[CrisisSignal] = set(self.signals)
        self.signals = (*self.signals, *(signal for signal in signals if signal not in known))
        if any(signal.category.is_crisis for signal in signals):
            self.mark_crisis()

    def mark_crisis(self) -> None:
        """Переводит чат в кризисный сценарий, вопросы больше не задаются."""
        self.stage = ChatStage.CRISIS
        self.pending = None

    def post_message(self, text: str) -> None:
        """Принимает свободную реплику после сводки или в кризисе."""
        self._validate_stage(ChatStage.SUMMARY, ChatStage.CRISIS, action="post a free message")
        self.record(MessageRole.USER, text)

    def record(self, role: MessageRole, text: str) -> None:
        """Добавляет реплику в историю; хранятся последние `HISTORY_LIMIT`."""
        message: Message = Message(role=role, text=text)
        self.messages = (*self.messages, message)[-self.HISTORY_LIMIT :]

    def _ask(self, question: Question) -> None:
        """Отмечает вопрос заданным и ждёт ответа."""
        self.pending = question
        self.asked = (*self.asked, question.fact)

    def _check_crisis(self) -> None:
        """Переводит в кризис, если скрининг — активные мысли или план."""
        if self.facts.self_harm is not None and self.facts.self_harm.is_crisis:
            self.mark_crisis()

    def _needs_self_harm_follow_up(self, inference: InferenceResult) -> bool:
        """Нужен ли повторный вопрос о самоповреждении."""
        return (
            not self.is_crisis
            and not self.finished
            and not self.self_harm_followed_up
            and Referral.CRISIS_HELPLINE in inference.referrals
            and self.facts.self_harm is SelfHarmScreening.UNKNOWN
        )

    @staticmethod
    def _validate_consent(*, consent: bool) -> None:
        """Без согласия на обработку данных диалог не начинается."""
        if not consent:
            raise ConsentRequiredError

    def _validate_pending(self) -> None:
        """Отвечать можно только на заданный вопрос."""
        if self.pending is None:
            raise ChatStageError(action="answer without a pending question", stage=self.stage)

    def _validate_can_conclude(self, questionnaire: Questionnaire) -> None:
        """Итог — когда вопросы кончились или диалог завершён, в кризисе — сразу."""
        if self.is_crisis:
            return
        if self.pending is not None:
            raise ChatStageError(action="conclude with a pending question", stage=self.stage)
        if not self.finished and questionnaire.next_question(self.facts, self.asked) is not None:
            raise ChatStageError(action="conclude before the questions are over", stage=self.stage)

    def _validate_stage(self, *stages: ChatStage, action: str) -> None:
        """Действие допустимо только на перечисленных этапах."""
        if self.stage not in stages:
            raise ChatStageError(action=action, stage=self.stage)
