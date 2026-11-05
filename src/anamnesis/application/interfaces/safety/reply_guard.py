from abc import abstractmethod
from typing import Protocol

from anamnesis.domain.enums.urgency_level import UrgencyLevel
from anamnesis.domain.types import LanguageCode
from anamnesis.domain.value_objects.reply_violation import ReplyViolation


class IReplyGuard(Protocol):
    @abstractmethod
    async def check(
        self,
        text: str,
        language: LanguageCode,
        level: UrgencyLevel | None,
    ) -> tuple[ReplyViolation, ...]: ...
