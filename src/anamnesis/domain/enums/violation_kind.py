from enum import StrEnum, auto


class ViolationKind(StrEnum):
    """Что недопустимо в ответе системы.

    Attributes:
        DIAGNOSIS: Утверждение диагноза или код МКБ.
        MEDICATION: Название лекарства или совет по медикаментам.
        PROMISE: Обещание результата.
        DEVALUATION: Обесценивание переживаний.
        STOP_TREATMENT: Совет прекратить лечение.
        LEVEL_MISMATCH: Уровень срочности, отличный от вычисленного правилами.
    """

    DIAGNOSIS = auto()
    MEDICATION = auto()
    PROMISE = auto()
    DEVALUATION = auto()
    STOP_TREATMENT = auto()
    LEVEL_MISMATCH = auto()
