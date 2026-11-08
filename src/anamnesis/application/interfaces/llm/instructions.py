from abc import abstractmethod
from enum import StrEnum, auto
from typing import Protocol


class Instruction(StrEnum):
    """Фиксированные инструкции языковой модели по задачам."""

    EXTRACTION = auto()
    SUMMARY = auto()
    REPLY = auto()
    CORRECTION = auto()


class IInstructions(Protocol):
    @abstractmethod
    def text(self, instruction: Instruction) -> str: ...
