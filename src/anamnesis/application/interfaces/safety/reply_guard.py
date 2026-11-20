from abc import abstractmethod
from enum import StrEnum, auto
from typing import Annotated, Protocol

from pydantic import StringConstraints

from anamnesis.application.dto.base import DTO
from anamnesis.domain.enums.recommendation import UrgencyLevel
from anamnesis.domain.types import LanguageCode


class ViolationKind(StrEnum):
    """Что недопустимо в ответе системы.

    Attributes:
        DIAGNOSIS: Утверждение диагноза или код МКБ.
        MEDICATION: Название лекарства или совет по медикаментам.
        PROMISE: Обещание результата.
        DEVALUATION: Обесценивание переживаний.
        STOP_TREATMENT: Совет прекратить лечение.
        LEVEL_MISMATCH: Уровень срочности, отличный от вычисленного правилами.
    """

    DIAGNOSIS = auto()
    MEDICATION = auto()
    PROMISE = auto()
    DEVALUATION = auto()
    STOP_TREATMENT = auto()
    LEVEL_MISMATCH = auto()


class ReplyViolation(DTO):
    """Недопустимый фрагмент ответа системы.

    Attributes:
        kind: Вид нарушения.
        quote: Фрагмент ответа; пробелы по краям обрезаются, пустой недопустим.
    """

    kind: ViolationKind
    quote: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class IReplyGuard(Protocol):
    @abstractmethod
    async def check(
        self,
        text: str,
        language: LanguageCode,
        level: UrgencyLevel | None,
    ) -> tuple[ReplyViolation, ...]: ...
