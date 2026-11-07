from abc import abstractmethod
from typing import Protocol

from anamnesis.application.dto.estimate import Estimate
from anamnesis.domain.value_objects.case_facts import CaseFacts


class IFactNormalizer(Protocol):
    """Перевод оценки по словам пользователя в чёткие сведения для правил."""

    @abstractmethod
    def normalize(self, estimate: Estimate) -> CaseFacts:
        """Значение сведения; у размытой оценки — ещё и уверенность в нём."""
