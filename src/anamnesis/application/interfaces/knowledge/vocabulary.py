from abc import abstractmethod
from collections.abc import Mapping
from typing import Protocol

from anamnesis.application.dto.base import DTO
from anamnesis.domain.types import TermId


class Vocabulary(DTO):
    """Понятия онтологии для извлечения сведений.

    Attributes:
        manifestations: Представители понятий-проявлений (`Anxiety_`).
        stressors: Представители понятий-стрессоров (`WorkStressor_`).
        reserved: Понятия, которые утверждает только детерминированный
            контур: маркеры риска и мысли о самоповреждении.
        concepts: Понятие каждого термина: `feel_anxious` → `Anxiety_`.
    """

    manifestations: frozenset[TermId]
    stressors: frozenset[TermId]
    reserved: frozenset[TermId]
    concepts: Mapping[TermId, TermId]


class IOntologyVocabulary(Protocol):
    @abstractmethod
    def vocabulary(self) -> Vocabulary: ...
