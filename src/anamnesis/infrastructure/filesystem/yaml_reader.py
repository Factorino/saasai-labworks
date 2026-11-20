from pathlib import Path
from typing import ClassVar

from pydantic import BaseModel, ConfigDict
import yaml


class YamlFile(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")


def read_yaml[FileT: YamlFile](path: Path, schema: type[FileT]) -> FileT:
    with path.open(encoding="utf-8") as file:
        content: object = yaml.safe_load(file)
    return schema.model_validate(content)
