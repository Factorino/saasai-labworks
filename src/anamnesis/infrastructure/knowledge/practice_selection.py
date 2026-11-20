from pathlib import Path
from types import MappingProxyType

from pydantic import Field

from anamnesis.domain.enums.recommendation import UrgencyLevel
from anamnesis.domain.services.practice_selection import LevelSelections, PracticeSelection
from anamnesis.domain.types import TermId
from anamnesis.domain.value_objects.practice import LevelSelection
from anamnesis.infrastructure.filesystem.yaml_reader import YamlFile, read_yaml


class LevelEntry(YamlFile):
    """Подбор практик на одном уровне.

    Attributes:
        limit: Сколько практик показать.
        excluded: Практики, которые на этом уровне лучше выполнять со специалистом.
    """

    limit: int = Field(ge=1)
    excluded: frozenset[TermId] = frozenset()

    def to_selection(self) -> LevelSelection:
        """Правило подбора домена по записи файла."""
        return LevelSelection(limit=self.limit, excluded=self.excluded)


class PracticeSelectionFile(YamlFile):
    """`knowledge/practice_selection.yaml`: подбор практик по уровням срочности.

    Уровня нет в файле — на нём практики не показываются.

    Attributes:
        L0: Уровень `L0`.
        L1: Уровень `L1`.
        L2: Уровень `L2`.
        L3: Уровень `L3`.
        insufficient_data: Уровень не определён.
    """

    L0: LevelEntry | None = None
    L1: LevelEntry | None = None
    L2: LevelEntry | None = None
    L3: LevelEntry | None = None
    insufficient_data: LevelEntry | None = None

    def selections(self) -> LevelSelections:
        """Правила подбора по уровням; `None` — уровень не определён."""
        entries: dict[UrgencyLevel | None, LevelEntry | None] = {
            UrgencyLevel.L0: self.L0,
            UrgencyLevel.L1: self.L1,
            UrgencyLevel.L2: self.L2,
            UrgencyLevel.L3: self.L3,
            None: self.insufficient_data,
        }

        selections: LevelSelections = MappingProxyType(
            {level: entry.to_selection() for level, entry in entries.items() if entry is not None},
        )
        return selections


def load_practice_selection(path: Path) -> PracticeSelection:
    """Подбор практик по файлу знаний."""
    document: PracticeSelectionFile = read_yaml(path, PracticeSelectionFile)
    return PracticeSelection(document.selections())
