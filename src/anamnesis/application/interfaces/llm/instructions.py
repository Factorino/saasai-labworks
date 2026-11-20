from abc import abstractmethod
from enum import StrEnum, auto
from typing import Protocol

from anamnesis.application.dto.base import DTO
from anamnesis.domain.types import TermId


class Instruction(StrEnum):
    """Неизменные инструкции языковой модели по задачам."""

    SUMMARY = auto()
    REPLY = auto()
    CORRECTION = auto()


class ConceptEntry(DTO):
    """Строка перечня понятий в инструкции извлечения.

    Attributes:
        term: Представитель понятия: идентификатор, который модель возвращает.
        name: Название на языке реплики.
        description: Описание; пустое, если его нет.
    """

    term: TermId
    name: str
    description: str = ""


class IInstructions(Protocol):
    """Инструкции языковой модели из фиксированных файлов.

    Весь текст промптов живёт в файлах инструкций; приложение передаёт только
    данные для подстановки.
    """

    @abstractmethod
    def text(self, instruction: Instruction) -> str:
        """Неизменная инструкция задачи."""

    @abstractmethod
    def extraction(
        self,
        manifestations: tuple[ConceptEntry, ...],
        stressors: tuple[ConceptEntry, ...],
    ) -> str:
        """Инструкция извлечения с перечнями допустимых понятий.

        Args:
            manifestations: Понятия-проявления в порядке перечня.
            stressors: Понятия-стрессоры в порядке перечня.

        Returns:
            Текст инструкции, в который подставлены перечни.
        """
