from abc import abstractmethod
from typing import Protocol

from anamnesis.application.dto.base import DTO
from anamnesis.domain.types import LanguageCode, TermId


class Helpline(DTO):
    """Служба помощи.

    Attributes:
        name: Название службы.
        phone: Номер телефона.
        note: Пояснение: часы работы, для кого служба.
    """

    name: str
    phone: str
    note: str = ""


class PracticeSource(DTO):
    """Открытый источник, который пересказывает документ практики.

    Attributes:
        title: Название источника.
        url: Ссылка.
    """

    title: str
    url: str


class PracticeGuide(DTO):
    """Документ практики самопомощи.

    Attributes:
        steps: Шаги выполнения.
        limits: Ограничения: когда практика не подходит.
        sources: Источники.
    """

    steps: tuple[str, ...]
    limits: tuple[str, ...] = ()
    sources: tuple[PracticeSource, ...]


class IKnowledgeBase(Protocol):
    """Справочные материалы на языке чата: документы практик и контакты служб помощи.

    Язык должен быть поддерживаемым: это проверяется при старте чата. На
    неизвестном языке реализация выбрасывает `UnsupportedLanguageError`.
    """

    @abstractmethod
    def helplines(self, language: LanguageCode) -> tuple[Helpline, ...]:
        """Контакты служб помощи для региона языка."""

    @abstractmethod
    def practice_guide(self, language: LanguageCode, practice: TermId) -> PracticeGuide | None:
        """Документ практики; `None`, если его нет."""
