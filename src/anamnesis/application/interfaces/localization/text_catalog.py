from abc import abstractmethod
from typing import Protocol

from anamnesis.application.dto.views.summary import HelplineView
from anamnesis.domain.enums.chat_stage import ChatStage
from anamnesis.domain.enums.fact_kind import FactKind
from anamnesis.domain.enums.referral import Referral
from anamnesis.domain.enums.urgency_level import UrgencyLevel
from anamnesis.domain.types import LanguageCode, OptionCode, RuleId, TermId
from anamnesis.domain.value_objects.question import Question


class ITextCatalog(Protocol):
    """Тексты для пользователя по кодам домена на выбранном языке."""

    @abstractmethod
    def supports(self, language: LanguageCode) -> bool:
        """Есть ли тексты и словарь терминов для языка."""

    @abstractmethod
    def greeting(self, language: LanguageCode) -> str:
        """Приглашение рассказать, что беспокоит."""

    @abstractmethod
    def crisis_message(self, language: LanguageCode) -> str:
        """Фиксированное сообщение в момент кризиса; контакты помощи идут отдельно."""

    @abstractmethod
    def support_others(self, language: LanguageCode) -> str:
        """Совет, как поддержать близкого, о котором тревожится пользователь."""

    @abstractmethod
    def helplines(self, language: LanguageCode) -> tuple[HelplineView, ...]:
        """Контакты служб помощи для региона языка."""

    @abstractmethod
    def question(self, question: Question, language: LanguageCode) -> str:
        """Формулировка вопроса, в том числе повторного."""

    @abstractmethod
    def option(self, fact: FactKind, code: OptionCode, language: LanguageCode) -> str:
        """Подпись варианта ответа."""

    @abstractmethod
    def approximate(self, fact: FactKind, language: LanguageCode) -> str:
        """Отметка, что сведение оценено приблизительно, по размытым словам."""

    @abstractmethod
    def disclaimer(self, language: LanguageCode) -> str:
        """Предупреждение, что сводка — не диагноз."""

    @abstractmethod
    def level(self, level: UrgencyLevel | None, language: LanguageCode) -> str:
        """Формулировка уровня; для `None` — «недостаточно данных»."""

    @abstractmethod
    def specialist(self, level: UrgencyLevel | None, language: LanguageCode) -> str:
        """Общая подсказка, к какому специалисту обратиться при таком уровне."""

    @abstractmethod
    def referral(self, referral: Referral, language: LanguageCode) -> str:
        """Совет, куда обратиться за помощью."""

    @abstractmethod
    def rule(self, rule: RuleId, language: LanguageCode) -> str:
        """Объяснение сработавшего правила."""

    @abstractmethod
    def term(self, term: TermId, language: LanguageCode) -> str:
        """Название понятия онтологии: кластера, практики, проявления, сферы."""

    @abstractmethod
    def description(self, term: TermId, language: LanguageCode) -> str:
        """Описание понятия онтологии; пустое, если его нет."""

    @abstractmethod
    def source(self, term: TermId, language: LanguageCode) -> str | None:
        """Источник практики; `None`, если его нет."""

    @abstractmethod
    def reply(self, stage: ChatStage, language: LanguageCode) -> str:
        """Шаблонный ответ на свободную реплику после сводки или в кризисе."""
