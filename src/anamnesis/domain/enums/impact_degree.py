from enum import IntEnum


class ImpactDegree(IntEnum):
    """Насколько проявления мешают жить.

    Значения совпадают со шкалой свойства онтологии `impactDegree` (0–3).

    Attributes:
        NONE: Почти не мешают.
        MILD: Немного мешают.
        MODERATE: Заметно мешают.
        SEVERE: Не получается справляться с обычными делами.
    """

    NONE = 0
    MILD = 1
    MODERATE = 2
    SEVERE = 3
