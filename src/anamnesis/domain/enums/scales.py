from enum import IntEnum


class Frequency(IntEnum):
    """Как часто бывают проявления.

    Значения совпадают со шкалой свойства онтологии `frequency` (0–3).
    Порог правил R12 и R14 (`frequency >= 2`) — это `FREQUENT`.

    Attributes:
        RARE: Редко, время от времени.
        INTERMITTENT: Несколько раз в неделю.
        FREQUENT: Большую часть дней.
        CONSTANT: Почти всё время.
    """

    RARE = 0
    INTERMITTENT = 1
    FREQUENT = 2
    CONSTANT = 3


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
