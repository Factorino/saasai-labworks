from enum import StrEnum, auto


class SelfHarmScreening(StrEnum):
    """Ответ на скрининговый вопрос о самоповреждении.

    Значения совпадают со строками свойства онтологии `selfHarmScreening`.

    Attributes:
        NONE: Таких мыслей нет.
        PASSIVE: Пассивные мысли о смерти: L2 и службы помощи.
        ACTIVE: Активные мысли причинить себе вред: L3, кризис.
        PLAN: Есть план: L3, кризис.
        UNKNOWN: Ответа нет: отказ или вопрос не задавался. Отличает
            «ответил „нет“» от «не ответил».
    """

    NONE = auto()
    PASSIVE = auto()
    ACTIVE = auto()
    PLAN = auto()
    UNKNOWN = auto()

    @property
    def is_crisis(self) -> bool:
        """Ведёт ли ответ в кризисный сценарий: активные мысли или план."""
        return self in {SelfHarmScreening.ACTIVE, SelfHarmScreening.PLAN}
