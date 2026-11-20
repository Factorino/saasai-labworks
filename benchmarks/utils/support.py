from collections.abc import Mapping
import os
from pathlib import Path
from typing import Final

import pandas as pd
import yaml


_BENCHMARK_DIR: Final[Path] = Path(__file__).resolve().parents[1]


def use_project_root() -> None:
    """Разрешить относительные пути настроек от корня проекта."""
    os.chdir(_BENCHMARK_DIR.parent)


def load_data(filename: str) -> object:
    """Загрузить набор данных из каталога бенчмарков."""
    path: Path = _BENCHMARK_DIR / "data" / filename
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def make_table(
    values: Mapping[str, object],
    *,
    decimals: int | None = None,
) -> pd.DataFrame:
    """Собрать однострочную сводку с сохранением порядка столбцов."""
    table: pd.DataFrame = pd.DataFrame([dict(values)])
    return table if decimals is None else table.round(decimals)
