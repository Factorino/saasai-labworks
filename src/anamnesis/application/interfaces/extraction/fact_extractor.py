from abc import abstractmethod
from typing import Protocol

from anamnesis.domain.types import LanguageCode
from anamnesis.domain.value_objects.case_facts import CaseFacts


class IFactExtractor(Protocol):
    """Извлечение сведений о случае из реплики пользователя."""

    @abstractmethod
    async def extract(self, text: str, language: LanguageCode) -> CaseFacts:
        """Находит в тексте термины онтологии и другие сведения с цитатами."""
