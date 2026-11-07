from enum import StrEnum, auto
from typing import Final


class FactKind(StrEnum):
    """Вид сведений о случае.

    Связывает вопрос, поле `CaseFacts`, которое он заполняет, и отметку об
    отказе. Значения служат ключами вопросов в файлах локализации. Стрессоры
    отдельно не спрашиваются: они приходят только из рассказа.

    Attributes:
        MANIFESTATIONS: Проявления (`hasManifestation`).
        DURATION: Длительность (`durationWeeks`).
        FREQUENCY: Частота (`frequency`).
        IMPACT: Влияние на жизнь (`impactDegree`).
        AFFECTED_DOMAINS: Затронутые сферы жизни (`affectsDomain`).
        SELF_HARM: Скрининг самоповреждения (`selfHarmScreening`).
        SLEEP: Изменение сна; в онтологию не передаётся.
        APPETITE: Изменение аппетита; в онтологию не передаётся.
        ENERGY: Изменение энергии; в онтологию не передаётся.
        SUBSTANCE_USE: Употребление веществ, чтобы стало легче.
        GOAL: Чего человек хочет от встречи со специалистом.
    """

    MANIFESTATIONS = auto()
    DURATION = auto()
    FREQUENCY = auto()
    IMPACT = auto()
    AFFECTED_DOMAINS = auto()
    SELF_HARM = auto()
    SLEEP = auto()
    APPETITE = auto()
    ENERGY = auto()
    SUBSTANCE_USE = auto()
    GOAL = auto()


REQUIRED_FACTS: Final[frozenset[FactKind]] = frozenset(
    {
        FactKind.MANIFESTATIONS,
        FactKind.DURATION,
        FactKind.FREQUENCY,
        FactKind.IMPACT,
        FactKind.SELF_HARM,
    },
)
"""Сведения, без которых уровень L0 не утверждается."""

ESTIMATED_FACTS: Final[frozenset[FactKind]] = frozenset(
    {
        FactKind.DURATION,
        FactKind.FREQUENCY,
        FactKind.IMPACT,
    },
)
"""Сведения, которые можно оценить по словам пользователя через лингвистические переменные."""
