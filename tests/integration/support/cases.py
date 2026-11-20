from enum import Enum
from pathlib import Path
from typing import Annotated, Final

from pydantic import BeforeValidator

from anamnesis.domain.enums.recommendation import UrgencyLevel
from anamnesis.domain.enums.scales import Frequency, ImpactDegree
from anamnesis.infrastructure.filesystem.yaml_reader import YamlFile, read_yaml


DATA_DIR: Final[Path] = Path(__file__).parents[1] / "data"
"""Файлы случаев; каждый читается своей моделью, неизвестный ключ — ошибка."""

type FrequencyName = Annotated[Frequency, by_name(Frequency)]
"""Частота именем шкалы: в случаях понятнее, чем код 0–3."""

type ImpactName = Annotated[ImpactDegree, by_name(ImpactDegree)]
"""Влияние на жизнь именем шкалы."""

type LevelName = Annotated[UrgencyLevel, by_name(UrgencyLevel)]
"""Уровень срочности именем: `L0`–`L3`."""


class UserMessage(YamlFile):
    """Реплика пользователя в сценарии.

    Attributes:
        text: Свой текст.
        options: Коды выбранных вариантов.
    """

    text: str = ""
    options: tuple[str, ...] = ()


def by_name[EnumT: Enum](enum: type[EnumT]) -> BeforeValidator:
    """Член перечисления по имени без учёта регистра: `frequent`, `L2`."""

    def parse(value: object) -> object:
        return enum[value.upper()] if isinstance(value, str) else value

    return BeforeValidator(parse)


def read_cases[FileT: YamlFile](name: str, schema: type[FileT]) -> FileT:
    """Файл случаев `data/<name>.yaml`, прочитанный моделью `schema`."""
    return read_yaml(DATA_DIR / f"{name}.yaml", schema)
