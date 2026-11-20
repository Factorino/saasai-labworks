from abc import abstractmethod
from typing import Protocol

from anamnesis.domain.types import LanguageCode, TermId


class IConceptTexts(Protocol):
    """Названия и описания понятий онтологии на языке чата.

    Нужны и сводке, и извлечению: модель получает перечень понятий с названиями
    на языке реплики. Язык должен быть поддерживаемым: это проверяется при старте
    чата. На неизвестном языке реализация выбрасывает `UnsupportedLanguageError`.
    """

    @abstractmethod
    def name(self, language: LanguageCode, term: TermId) -> str:
        """Название понятия; без перевода — его идентификатор."""

    @abstractmethod
    def description(self, language: LanguageCode, term: TermId) -> str:
        """Описание понятия; пустое, если его нет."""
