from pathlib import Path
from types import MappingProxyType
from typing import TYPE_CHECKING, override

from anamnesis.application.interfaces.llm.instructions import IInstructions, Instruction


if TYPE_CHECKING:
    from collections.abc import Mapping


class FileInstructions(IInstructions):
    """Инструкции из файлов `<каталог>/<задача>.md`, прочитанные при запуске."""

    def __init__(self, directory: Path) -> None:
        self._texts: Mapping[Instruction, str] = MappingProxyType(
            {
                instruction: (directory / f"{instruction}.md").read_text(encoding="utf-8").strip()
                for instruction in Instruction
            },
        )

    @override
    def text(self, instruction: Instruction) -> str:
        return self._texts[instruction]
