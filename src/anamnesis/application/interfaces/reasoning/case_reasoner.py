from abc import abstractmethod
from typing import Protocol

from anamnesis.domain.value_objects.case_facts import CaseFacts
from anamnesis.domain.value_objects.inference import InferenceResult


class ICaseReasoner(Protocol):
    """Машина вывода по онтологии: SWRL-правила над сведениями о случае."""

    @abstractmethod
    async def infer(self, facts: CaseFacts) -> InferenceResult:
        """Строит индивид `Case` по сведениям и возвращает то, что вывели правила."""
