from enum import IntEnum


class Frequency(IntEnum):
    """Как часто бывают проявления.

    Значения совпадают со шкалой свойства онтологии `frequency` (0–3).

    Attributes:
        RARELY: Редко, время от времени.
        SEVERAL_TIMES_A_WEEK: Несколько раз в неделю.
        MOST_DAYS: Большую часть дней.
        CONSTANTLY: Почти всё время.
    """

    RARELY = 0
    SEVERAL_TIMES_A_WEEK = 1
    MOST_DAYS = 2
    CONSTANTLY = 3
