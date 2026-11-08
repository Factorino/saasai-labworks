from pathlib import Path
from typing import Any, ClassVar, Final

from pydantic import BaseModel, ConfigDict, Field
import yaml

from anamnesis.domain.enums.urgency_level import UrgencyLevel
from anamnesis.domain.services.practice_selection import LevelSelection, PracticeSelection
from anamnesis.domain.types import TermId


_UNDEFINED_LEVEL_KEY: Final[str] = "insufficient_data"
"""Ключ уровня «недостаточно данных» в файле."""


class _Level(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")

    limit: int = Field(ge=1)
    excluded: frozenset[TermId] = frozenset()


def load_practice_selection(path: Path) -> PracticeSelection:
    """Правила подбора практик из файла знаний."""
    with path.open(encoding="utf-8") as file:
        data: dict[str, Any] = yaml.safe_load(file)
    return PracticeSelection(
        {
            None if key == _UNDEFINED_LEVEL_KEY else UrgencyLevel[key]: LevelSelection(
                limit=parsed.limit,
                excluded=parsed.excluded,
            )
            for key, parsed in ((key, _Level.model_validate(raw)) for key, raw in data.items())
        },
    )
