from collections.abc import Mapping
from dataclasses import field
from datetime import datetime
from types import MappingProxyType
from typing import ClassVar, Final, NewType
from uuid import UUID

from anamnesis.domain.entities.base import Entity, entity
from anamnesis.domain.enums.chat import ChatStage, MessageRole
from anamnesis.domain.enums.crisis import SelfHarmScreening
from anamnesis.domain.enums.fact_kind import FactKind
from anamnesis.domain.enums.recommendation import Referral
from anamnesis.domain.errors.chat import ChatStageError, ConsentRequiredError
from anamnesis.domain.services.assessment import AssessmentService
from anamnesis.domain.services.questionnaire import Questionnaire
from anamnesis.domain.types import LanguageCode
from anamnesis.domain.value_objects.assessment import Assessment
from anamnesis.domain.value_objects.case_facts import CaseFacts
from anamnesis.domain.value_objects.clarification import Answer, Question
from anamnesis.domain.value_objects.crisis_signal import CrisisSignal
from anamnesis.domain.value_objects.inference import InferenceResult
from anamnesis.domain.value_objects.message import Message
from anamnesis.domain.value_objects.narrative import Narrative


type _Transitions = Mapping[ChatStage, frozenset[ChatStage]]
"""Граф этапов: куда можно перейти из каждого этапа."""

_TRANSITIONS: Final[_Transitions] = MappingProxyType(
    {
        ChatStage.STORY: frozenset({ChatStage.CLARIFYING, ChatStage.FINISHED, ChatStage.CRISIS}),
        ChatStage.CLARIFYING: frozenset({ChatStage.FINISHED, ChatStage.SUMMARY, ChatStage.CRISIS}),
        ChatStage.FINISHED: frozenset({ChatStage.SUMMARY, ChatStage.CRISIS}),
        ChatStage.SUMMARY: frozenset({ChatStage.CRISIS}),
        ChatStage.CRISIS: frozenset(),
    },
)
"""Граф этапов: куда можно перейти из каждого. Из кризиса выхода нет."""

ChatId = NewType("ChatId", UUID)
"""Идентификатор чата."""


@entity
class Chat(Entity[ChatId]):
    """Диалог с одним пользователем.

    Этап меняется только через `_move_to` по графу `_TRANSITIONS`. Неотвеченный
    вопрос бывает только на этапе `CLARIFYING`, оценка на этапе `SUMMARY` есть всегда.

    Attributes:
        language: Язык диалога: по нему извлекаются термины и подбираются тексты.
        created_at: Когда начат диалог.
        stage: Текущий этап.
        facts: Накопленные сведения о случае.
        asked: Заданные вопросы по порядку, включая повторный.
        pending: Вопрос, который ждёт ответа.
        assessment: Выданная оценка.
        narrative: Текст сводки для человека; `None` — показывается шаблон.
        messages: Последние `HISTORY_LIMIT` реплик.
        signals: Находки кризисного детектора за весь диалог.
    """

    HISTORY_LIMIT: ClassVar[int] = 20

    language: LanguageCode
    created_at: datetime

    stage: ChatStage = ChatStage.STORY

    facts: CaseFacts = field(default_factory=CaseFacts)
    asked: tuple[Question, ...] = ()
    pending: Question | None = None

    assessment: Assessment | None = None
    narrative: Narrative | None = None

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
    ) -> "Chat":
        """Начинает диалог."""
        cls._validate_consent(consent=consent)
        chat: Chat = cls(id=chat_id, language=language, created_at=now)
        return chat

    @staticmethod
    def _validate_consent(*, consent: bool) -> None:
        """Без согласия на обработку данных диалог не начинается."""
        if not consent:
            raise ConsentRequiredError

    @property
    def is_crisis(self) -> bool:
        """Чат в кризисном сценарии."""
        return self.stage is ChatStage.CRISIS

    @property
    def self_harm_followed_up(self) -> bool:
        """Повторный вопрос о самоповреждении уже задан."""
        return any(question.follow_up for question in self.asked)

    @property
    def _asked_facts(self) -> tuple[FactKind, ...]:
        """Виды заданных вопросов: по ним опросник выбирает следующий."""
        return tuple(question.fact for question in self.asked)

    def tell_story(self, text: str, extracted: CaseFacts) -> None:
        """Принимает свободный рассказ о том, что беспокоит."""
        self._validate_stage(ChatStage.STORY, action="tell the story")
        self.record(MessageRole.USER, text)
        self.facts = self.facts.absorb(text, extracted)
        self._move_to(ChatStage.CLARIFYING)
        self._check_crisis()

    def next_question(self, questionnaire: Questionnaire) -> Question | None:
        """Неотвеченный вопрос или следующий по опроснику."""
        self._validate_stage(ChatStage.CLARIFYING, action="ask a question")

        if self.pending is not None:
            return self.pending

        question: Question | None = questionnaire.next_question(self.facts, self._asked_facts)
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
        question: Question | None = self.pending
        if question is None:
            raise ChatStageError(action="answer without a pending question", stage=self.stage)

        self.facts = questionnaire.apply(self.facts, question, answer, extracted)
        self.pending = None

        self._check_crisis()
        return question

    def finish(self) -> None:
        """Завершает диалог, не дожидаясь конца вопросов."""
        self._validate_stage(ChatStage.STORY, ChatStage.CLARIFYING, action="finish the dialogue")
        self._move_to(ChatStage.FINISHED)

    def conclude(
        self,
        inference: InferenceResult,
        assessment_service: AssessmentService,
        questionnaire: Questionnaire,
    ) -> Question | Assessment:
        """Подводит итог по результату вывода; вместо итога может задать повторный вопрос."""
        self._validate_stage(
            ChatStage.CLARIFYING,
            ChatStage.FINISHED,
            ChatStage.CRISIS,
            action="conclude",
        )
        self._validate_can_conclude(questionnaire)

        if self._needs_self_harm_follow_up(inference):
            follow_up: Question = questionnaire.self_harm_follow_up
            self._ask(follow_up)
            return follow_up

        self.assessment = assessment_service.assess(
            self.facts,
            inference,
            crisis=self.is_crisis,
            signals=self.signals,
        )
        if not self.is_crisis:
            self._move_to(ChatStage.SUMMARY)
        return self.assessment

    def describe(self, narrative: Narrative | None) -> None:
        """Запоминает текст сводки, чтобы показывать его без повторной генерации."""
        self._validate_stage(ChatStage.SUMMARY, ChatStage.CRISIS, action="describe the summary")
        self.narrative = narrative

    def register_signals(self, signals: tuple[CrisisSignal, ...]) -> None:
        """Запоминает находки детектора; кризисная переводит чат в кризис на любом этапе."""
        known: set[CrisisSignal] = set(self.signals)
        self.signals = (*self.signals, *(signal for signal in signals if signal not in known))
        if any(signal.category.is_crisis for signal in signals):
            self.mark_crisis()

    def mark_crisis(self) -> None:
        """Переводит чат в кризисный сценарий, вопросы больше не задаются."""
        if not self.is_crisis:
            self._move_to(ChatStage.CRISIS)

    def post_message(self, text: str) -> None:
        """Принимает свободную реплику после сводки или в кризисе."""
        self._validate_stage(ChatStage.SUMMARY, ChatStage.CRISIS, action="post a free message")
        self.record(MessageRole.USER, text)

    def record(self, role: MessageRole, text: str) -> None:
        """Добавляет реплику в историю; хранятся последние `HISTORY_LIMIT`."""
        message: Message = Message(role=role, text=text)
        self.messages = (*self.messages, message)[-self.HISTORY_LIMIT :]

    def _validate_stage(self, *stages: ChatStage, action: str) -> None:
        """Действие допустимо только на перечисленных этапах."""
        if self.stage not in stages:
            raise ChatStageError(action=action, stage=self.stage)

    def _validate_can_conclude(self, questionnaire: Questionnaire) -> None:
        """Итог — когда вопросы кончились или диалог завершён, в кризисе — сразу."""
        if self.is_crisis or self.stage is ChatStage.FINISHED:
            return
        if self.pending is not None:
            raise ChatStageError(action="conclude with a pending question", stage=self.stage)
        if questionnaire.next_question(self.facts, self._asked_facts) is not None:
            raise ChatStageError(action="conclude before the questions are over", stage=self.stage)

    def _needs_self_harm_follow_up(self, inference: InferenceResult) -> bool:
        """Нужен ли повторный вопрос о самоповреждении.

        Только на этапе `CLARIFYING`: в кризисе итог сразу, после досрочного
        завершения вопросов больше нет.
        """
        return (
            self.stage is ChatStage.CLARIFYING
            and not self.self_harm_followed_up
            and Referral.CRISIS_HELPLINE in inference.referrals
            and self.facts.self_harm is SelfHarmScreening.UNKNOWN
        )

    def _check_crisis(self) -> None:
        """Переводит в кризис, если скрининг — активные мысли или план."""
        if self.facts.self_harm is not None and self.facts.self_harm.is_crisis:
            self.mark_crisis()

    def _ask(self, question: Question) -> None:
        """Отмечает вопрос заданным и ждёт ответа."""
        self.pending = question
        self.asked = (*self.asked, question)

    def _move_to(self, stage: ChatStage) -> None:
        """Переходит на этап по графу `_TRANSITIONS`; вне `CLARIFYING` вопросов не ждём.

        Raises:
            RuntimeError: Перехода нет в графе. Это ошибка программы: предусловия
                методов не должны его допускать.
        """
        if stage not in _TRANSITIONS[self.stage]:
            raise RuntimeError(f"Chat cannot move from {self.stage} to {stage}")
        if stage is not ChatStage.CLARIFYING:
            self.pending = None
        self.stage = stage
