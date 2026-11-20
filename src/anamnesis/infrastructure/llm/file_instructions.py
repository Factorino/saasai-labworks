from collections.abc import Mapping
from pathlib import Path
from string import Template
from types import MappingProxyType
from typing import Final, override

from anamnesis.application.interfaces.llm.instructions import (
    ConceptEntry,
    IInstructions,
    Instruction,
)


_EXTRACTION_FILE: Final[str] = "extraction.md"

_EXTRACTION_PLACEHOLDERS: Final[frozenset[str]] = frozenset({"manifestations", "stressors"})
"""Места для перечней понятий в инструкции извлечения: `$manifestations`, `$stressors`."""

_CONCEPT_LINE: Final[str] = "- {term}: {name}"
"""Строка перечня понятий в инструкции извлечения."""

_CONCEPT_DESCRIPTION: Final[str] = " — {description}"
"""Описание понятия в конце строки перечня, если оно есть."""


class FileInstructions(IInstructions):
    """Инструкции из файлов `<каталог>/<задача>.md`, прочитанные при запуске."""

    def __init__(self, *, texts: Mapping[Instruction, str], extraction: Template) -> None:
        self._texts: Mapping[Instruction, str] = MappingProxyType(dict(texts))
        self._extraction: Template = extraction

    @classmethod
    def load(cls, directory: Path) -> "FileInstructions":
        texts: dict[Instruction, str] = {
            instruction: cls._read(directory / f"{instruction}.md") for instruction in Instruction
        }
        extraction: Template = Template(cls._read(directory / _EXTRACTION_FILE))
        cls._validate_extraction(extraction)
        return cls(texts=texts, extraction=extraction)

    @classmethod
    def _concepts(cls, entries: tuple[ConceptEntry, ...]) -> str:
        """Перечень понятий: по строке на понятие."""
        return "\n".join(cls._concept(entry) for entry in entries)

    @staticmethod
    def _concept(entry: ConceptEntry) -> str:
        """Строка перечня: идентификатор и название, затем описание, если оно есть."""
        line: str = _CONCEPT_LINE.format(term=entry.term, name=entry.name)
        if entry.description:
            line += _CONCEPT_DESCRIPTION.format(description=entry.description)
        return line

    @staticmethod
    def _read(path: Path) -> str:
        return path.read_text(encoding="utf-8").strip()

    @staticmethod
    def _validate_extraction(template: Template) -> None:
        if not template.is_valid():
            raise ValueError("Extraction instruction has a '$' that is not a placeholder")

        placeholders: set[str] = set(template.get_identifiers())
        if placeholders != _EXTRACTION_PLACEHOLDERS:
            raise ValueError(
                f"Extraction instruction must have placeholders "
                f"{sorted(_EXTRACTION_PLACEHOLDERS)}, found {sorted(placeholders)}",
            )

    @override
    def text(self, instruction: Instruction) -> str:
        return self._texts[instruction]

    @override
    def extraction(
        self,
        manifestations: tuple[ConceptEntry, ...],
        stressors: tuple[ConceptEntry, ...],
    ) -> str:
        return self._extraction.substitute(
            manifestations=self._concepts(manifestations),
            stressors=self._concepts(stressors),
        )
