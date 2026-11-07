from abc import abstractmethod
from typing import Protocol

from anamnesis.application.dto.estimate import Estimate
from anamnesis.domain.enums.fact_kind import FactKind
from anamnesis.domain.types import LanguageCode


class IEstimateExtractor(Protocol):
    """Оценка длительности, частоты или влияния по словам пользователя."""

    @abstractmethod
    async def extract(self, text: str, fact: FactKind, language: LanguageCode) -> Estimate | None:
        """Число из текста или степени термов по размытым выражениям; `None` — ничего нет."""
