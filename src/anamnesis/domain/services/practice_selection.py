from collections.abc import Collection, Iterable, Mapping
from types import MappingProxyType
from typing import Final

from anamnesis.domain.enums.recommendation import UrgencyLevel
from anamnesis.domain.errors.common import ValidationError
from anamnesis.domain.types import TermId
from anamnesis.domain.value_objects.practice import LevelSelection, PracticeAdvice


_SELF_HELP_LEVELS: Final[frozenset[UrgencyLevel | None]] = frozenset(
    {UrgencyLevel.L0, UrgencyLevel.L1, UrgencyLevel.L2, None},
)
"""Уровни, на которых советуется самопомощь; `None` — уровень не определён."""

type LevelSelections = Mapping[UrgencyLevel | None, LevelSelection]
"""Правила подбора практик по уровням; `None` — уровень не определён."""


class PracticeSelection:
    """Выбирает практики для сводки по кластерам случая и уровню срочности.

    Сначала каждый кластер получает самую специфичную для него практику,
    чтобы широкие не вытесняли точные: при бессоннице нужен совет о сне, а не
    только расслабление. Оставшиеся места занимают практики, подходящие
    большему числу кластеров. Практика с ограничением идёт после остальных.
    """

    def __init__(self, levels: LevelSelections) -> None:
        self._validate(levels)
        self._levels: LevelSelections = MappingProxyType(dict(levels))

    def select(
        self,
        advices: Iterable[PracticeAdvice],
        *,
        level: UrgencyLevel | None,
        clusters: Collection[TermId],
    ) -> tuple[PracticeAdvice, ...]:
        """Практики в порядке показа; на уровне без самопомощи их нет."""
        rule: LevelSelection | None = self._levels.get(level)
        if rule is None:
            return ()

        candidates: list[PracticeAdvice] = sorted(
            (advice for advice in advices if advice.practice not in rule.excluded),
            key=_priority,
        )

        chosen: dict[TermId, PracticeAdvice] = {}
        for cluster in clusters:
            for advice in sorted(candidates, key=_specificity):
                if cluster in advice.clusters and advice.practice not in chosen:
                    chosen[advice.practice] = advice
                    break

        for advice in candidates:
            chosen.setdefault(advice.practice, advice)

        practices: tuple[PracticeAdvice, ...] = tuple(
            sorted(list(chosen.values())[: rule.limit], key=_priority)
        )
        return practices

    def _validate(self, levels: LevelSelections) -> None:
        if frozenset(levels) != _SELF_HELP_LEVELS:
            raise ValidationError(
                subject=type(self).__name__,
                reason="levels must cover L0, L1, L2 and an undefined level",
            )


def _priority(advice: PracticeAdvice) -> tuple[bool, int, TermId]:
    return advice.needs_caution, -len(advice.clusters), advice.practice


def _specificity(advice: PracticeAdvice) -> tuple[bool, int, TermId]:
    return advice.needs_caution, len(advice.clusters), advice.practice
