from enum import StrEnum, auto


class Referral(StrEnum):
    """Куда обратиться за помощью помимо самопомощи.

    Соответствует ветви `Referral` онтологии.

    Attributes:
        EMERGENCY_MEDICAL_CARE: Срочная медицинская помощь.
        CRISIS_HELPLINE: Службы экстренной психологической помощи.
        DOCTOR_VISIT: Сначала обратиться к врачу.
    """

    EMERGENCY_MEDICAL_CARE = auto()
    CRISIS_HELPLINE = auto()
    DOCTOR_VISIT = auto()
