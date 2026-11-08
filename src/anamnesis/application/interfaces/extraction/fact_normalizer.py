from abc import abstractmethod
from typing import Protocol

from anamnesis.application.dto.estimate import Estimate, LinguisticTerm
from anamnesis.domain.enums.fact_kind import FactKind
from anamnesis.domain.value_objects.case_facts import CaseFacts


class IFactNormalizer(Protocol):
    """Перевод оценки по словам пользователя в чёткие сведения для правил."""

    @abstractmethod
    def terms(self, fact: FactKind) -> tuple[LinguisticTerm, ...]:
        """Термы лингвистической переменной сведения по возрастанию."""

    @abstractmethod
    def normalize(self, estimate: Estimate) -> CaseFacts:
        """Значение сведения; у размытой оценки — ещё и уверенность в нём."""
