from abc import abstractmethod
from typing import Protocol

from anamnesis.domain.enums.fact_kind import FactKind
from anamnesis.domain.enums.recommendation import Referral, UrgencyLevel
from anamnesis.domain.types import LanguageCode, RuleId


class ISummaryTexts(Protocol):
    """Тексты итоговой сводки на языке чата.

    Язык должен быть поддерживаемым: это проверяется при старте чата. На
    неизвестном языке реализация выбрасывает `UnsupportedLanguageError`.
    """

    @abstractmethod
    def level(self, language: LanguageCode, level: UrgencyLevel | None) -> str:
        """Формулировка уровня; для `None` — «недостаточно данных»."""

    @abstractmethod
    def specialist(self, language: LanguageCode, level: UrgencyLevel | None) -> str:
        """Подсказка, к какому специалисту обратиться при таком уровне."""

    @abstractmethod
    def referral(self, language: LanguageCode, referral: Referral) -> str:
        """Совет, куда обратиться за помощью."""

    @abstractmethod
    def rule(self, language: LanguageCode, rule: RuleId) -> str:
        """Объяснение сработавшего правила."""

    @abstractmethod
    def approximate(self, language: LanguageCode, fact: FactKind) -> str:
        """Отметка, что сведение оценено приблизительно, по размытым словам."""

    @abstractmethod
    def disclaimer(self, language: LanguageCode) -> str:
        """Предупреждение, что сводка — не диагноз."""

    @abstractmethod
    def fallback_description(self, language: LanguageCode) -> str:
        """Безопасный текст вместо описания состояния."""

    @abstractmethod
    def fallback_request(self, language: LanguageCode) -> str:
        """Безопасный текст вместо запроса к специалисту."""

    @abstractmethod
    def support_others(self, language: LanguageCode) -> str:
        """Совет, как поддержать близкого, о котором тревожится пользователь."""
