from abc import abstractmethod
from typing import Protocol

from anamnesis.domain.enums.chat import ChatStage
from anamnesis.domain.enums.fact_kind import FactKind
from anamnesis.domain.types import LanguageCode, OptionCode
from anamnesis.domain.value_objects.clarification import Question


class IDialogueTexts(Protocol):
    """Тексты хода диалога на языке чата.

    Язык должен быть поддерживаемым: это проверяется при старте чата. На
    неизвестном языке реализация выбрасывает `UnsupportedLanguageError`.
    """

    @abstractmethod
    def greeting(self, language: LanguageCode) -> str:
        """Приглашение рассказать, что беспокоит."""

    @abstractmethod
    def question(self, language: LanguageCode, question: Question) -> str:
        """Формулировка вопроса; у повторного — своя, если она есть, иначе основная."""

    @abstractmethod
    def option(self, language: LanguageCode, fact: FactKind, code: OptionCode) -> str:
        """Подпись варианта ответа; у отказа — общая, если у вопроса нет своей."""

    @abstractmethod
    def crisis_message(self, language: LanguageCode) -> str:
        """Фиксированное сообщение в момент кризиса; контакты помощи идут отдельно."""

    @abstractmethod
    def reply(self, language: LanguageCode, stage: ChatStage) -> str:
        """Шаблонный ответ на свободную реплику после сводки или в кризисе."""
