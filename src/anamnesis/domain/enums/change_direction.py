from enum import StrEnum, auto


class ChangeDirection(StrEnum):
    """Как изменились сон, аппетит или энергия по сравнению с обычным.

    Attributes:
        UNCHANGED: Как обычно.
        DECREASED: Стало меньше или хуже.
        INCREASED: Стало больше обычного.
    """

    UNCHANGED = auto()
    DECREASED = auto()
    INCREASED = auto()
