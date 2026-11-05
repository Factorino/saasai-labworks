from abc import abstractmethod
from typing import Protocol

from anamnesis.domain.types import LanguageCode
from anamnesis.domain.value_objects.crisis_signal import CrisisSignal


class ICrisisDetector(Protocol):
    """Кризисный детектор: работает без LLM и проверяет каждую реплику."""

    @abstractmethod
    async def detect(self, text: str, language: LanguageCode) -> tuple[CrisisSignal, ...]:
        """Находки в реплике; пусто, если ничего не найдено."""
