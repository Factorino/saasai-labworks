from enum import StrEnum, auto


class CrisisCategory(StrEnum):
    """Что нашёл кризисный детектор в реплике.

    Attributes:
        SUICIDE: Мысли или намерение покончить с собой.
        SELF_HARM: Причинение себе вреда.
        VIOLENCE: Намерение причинить вред другим.
        INDIRECT: Косвенные признаки: прощальные письма, раздача вещей.
        PASSIVE: Пассивные мысли о смерти; не кризис, но нужны службы помощи.
        OTHER_PERSON: Тревога за другого человека; не кризис самого пользователя.
    """

    SUICIDE = auto()
    SELF_HARM = auto()
    VIOLENCE = auto()
    INDIRECT = auto()
    PASSIVE = auto()
    OTHER_PERSON = auto()

    @property
    def is_crisis(self) -> bool:
        """Переводит ли находка чат в кризисный сценарий."""
        return self not in {CrisisCategory.PASSIVE, CrisisCategory.OTHER_PERSON}
