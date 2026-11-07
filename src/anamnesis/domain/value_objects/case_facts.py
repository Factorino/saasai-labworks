from collections.abc import Iterable, Mapping
from dataclasses import field
from types import MappingProxyType
from typing import Any, ClassVar, Final

from anamnesis.domain.enums.change_direction import ChangeDirection
from anamnesis.domain.enums.fact_kind import ESTIMATED_FACTS, REQUIRED_FACTS, FactKind
from anamnesis.domain.enums.frequency import Frequency
from anamnesis.domain.enums.impact_degree import ImpactDegree
from anamnesis.domain.enums.self_harm_screening import SelfHarmScreening
from anamnesis.domain.errors.common import ValidationError
from anamnesis.domain.types import TermId
from anamnesis.domain.value_objects.base import ValueObject, value_object
from anamnesis.domain.value_objects.duration import Duration
from anamnesis.domain.value_objects.evidence import Evidence


_SCALAR_ATTRS: Final[Mapping[FactKind, str]] = MappingProxyType(
    {
        FactKind.DURATION: "duration",
        FactKind.FREQUENCY: "frequency",
        FactKind.IMPACT: "impact",
        FactKind.SLEEP: "sleep",
        FactKind.APPETITE: "appetite",
        FactKind.ENERGY: "energy",
        FactKind.SUBSTANCE_USE: "substance_use",
        FactKind.GOAL: "goal",
    },
)
"""Поля сведений с одним значением: сведение известно, если значение задано."""


@value_object
class CaseFacts(ValueObject):
    """Всё, что известно о случае к текущему моменту.

    Из этих сведений инфраструктура строит индивид `Case` онтологии.
    Неизвестное сведение — `None` или пустая коллекция, а не ноль: иначе
    правила с порогами сработали бы на «нуле», и система утвердила бы L0 там,
    где данных просто нет.

    Attributes:
        manifestations: Найденные проявления (`hasManifestation`).
        stressors: Найденные стрессоры (`hasStressor`).
        unrecognized: Реплики, в которых не нашлось ни одного проявления.
        duration: Длительность (`durationWeeks`).
        frequency: Частота (`frequency`).
        impact: Влияние на жизнь (`impactDegree`).
        confidence: Уверенность в длительности, частоте и влиянии, оценённых по
            размытым словам: степень принадлежности чёткого значения терму.
            Значения из вариантов ответа и чисел точные, их здесь нет.
        affected_domains: Затронутые сферы (`affectsDomain`).
        self_harm: Скрининг самоповреждения (`selfHarmScreening`).
        sleep: Изменение сна; в онтологию не передаётся.
        appetite: Изменение аппетита; в онтологию не передаётся.
        energy: Изменение энергии; в онтологию не передаётся.
        substance_use: Употребляет ли человек вещества, чтобы стало легче.
        goal: Чего человек хочет от встречи со специалистом.
        refused: От каких вопросов человек отказался; их не задают повторно.
    """

    _FIELD_NAME: ClassVar[str] = "CaseFacts"
    _MAX_GOAL_LENGTH: ClassVar[int] = 1000
    """Предел длины цели обращения в символах."""

    manifestations: tuple[Evidence, ...] = ()
    stressors: tuple[Evidence, ...] = ()
    unrecognized: tuple[str, ...] = ()

    duration: Duration | None = None
    frequency: Frequency | None = None
    impact: ImpactDegree | None = None
    confidence: Mapping[FactKind, float] = field(default_factory=lambda: MappingProxyType({}))

    affected_domains: frozenset[TermId] = frozenset()

    self_harm: SelfHarmScreening | None = None

    sleep: ChangeDirection | None = None
    appetite: ChangeDirection | None = None
    energy: ChangeDirection | None = None
    substance_use: bool | None = None

    goal: str | None = None
    refused: frozenset[FactKind] = frozenset()

    def __post_init__(self) -> None:
        self._normalize()
        self._validate()

    @property
    def manifestation_terms(self) -> tuple[TermId, ...]:
        """Термины проявлений без цитат — для передачи в онтологию."""
        return tuple(evidence.term for evidence in self.manifestations)

    @property
    def stressor_terms(self) -> tuple[TermId, ...]:
        """Термины стрессоров без цитат — для передачи в онтологию."""
        return tuple(evidence.term for evidence in self.stressors)

    @property
    def missing_required(self) -> frozenset[FactKind]:
        """Каких обязательных сведений (`REQUIRED_FACTS`) не хватает."""
        return frozenset(kind for kind in REQUIRED_FACTS if not self.is_known(kind))

    @property
    def is_complete(self) -> bool:
        """Все обязательные сведения собраны."""
        return not self.missing_required

    def is_known(self, kind: FactKind) -> bool:
        """Известно ли сведение.

        Проявления и сферы известны, если найдено хоть одно. Скрининг
        самоповреждения с ответом `unknown` известным не считается.

        Args:
            kind: Вид сведений.

        Returns:
            `True`, если значение есть.
        """
        if kind is FactKind.MANIFESTATIONS:
            return bool(self.manifestations)
        if kind is FactKind.AFFECTED_DOMAINS:
            return bool(self.affected_domains)
        if kind is FactKind.SELF_HARM:
            return self.self_harm not in {None, SelfHarmScreening.UNKNOWN}
        return getattr(self, _SCALAR_ATTRS[kind]) is not None

    def is_approximate(self, kind: FactKind) -> bool:
        """Значение сведения оценено по размытым словам."""
        return kind in self.confidence

    def is_settled(self, kind: FactKind) -> bool:
        """Больше не нужно спрашивать: сведение известно или от него отказались."""
        return self.is_known(kind) or kind in self.refused

    def merge(self, newer: "CaseFacts") -> "CaseFacts":
        """Объединяет сведения: новое известное значение заменяет старое.

        Проявления, стрессоры, цитаты, сферы и отказы накапливаются без
        повторов. Ответ `unknown` уже известный скрининг не перекрывает.

        Args:
            newer: Сведения, полученные позже.

        Returns:
            Новый объект с объединёнными сведениями.
        """
        return CaseFacts(
            manifestations=self.manifestations + newer.manifestations,
            stressors=self.stressors + newer.stressors,
            unrecognized=self.unrecognized + newer.unrecognized,
            duration=_newer(self.duration, newer.duration),
            frequency=_newer(self.frequency, newer.frequency),
            impact=_newer(self.impact, newer.impact),
            confidence=self._merge_confidence(newer),
            affected_domains=self.affected_domains | newer.affected_domains,
            self_harm=self._merge_self_harm(newer.self_harm),
            sleep=_newer(self.sleep, newer.sleep),
            appetite=_newer(self.appetite, newer.appetite),
            energy=_newer(self.energy, newer.energy),
            substance_use=_newer(self.substance_use, newer.substance_use),
            goal=_newer(self.goal, newer.goal),
            refused=self.refused | newer.refused,
        )

    def refuse(self, kind: FactKind) -> "CaseFacts":
        """Отмечает отказ отвечать.

        Отказ от уже известного сведения ничего не меняет. Отказ от вопроса
        о самоповреждении даёт скрининг `unknown`.

        Args:
            kind: От какого сведения отказались.

        Returns:
            Новый объект с отметкой об отказе.
        """
        return self.merge(CaseFacts(refused=frozenset({kind})))

    def absorb(self, text: str, extracted: "CaseFacts") -> "CaseFacts":
        """Добавляет сведения, извлечённые из реплики.

        Args:
            text: Реплика пользователя. Если в ней не нашлось ни одного
                проявления, она сохраняется в `unrecognized`.
            extracted: Сведения, найденные в реплике вне домена.

        Returns:
            Новый объект с добавленными сведениями.
        """
        unrecognized: tuple[str, ...] = () if extracted.manifestations else (text,)
        return self.merge(extracted).merge(CaseFacts(unrecognized=unrecognized))

    def _merge_confidence(self, newer: "CaseFacts") -> Mapping[FactKind, float]:
        """Уверенность берётся вместе со значением: новое значение приносит свою."""
        merged: dict[FactKind, float] = {}
        for kind in ESTIMATED_FACTS:
            source: CaseFacts = newer if newer.is_known(kind) else self
            if kind in source.confidence:
                merged[kind] = source.confidence[kind]
        return MappingProxyType(merged)

    def _merge_self_harm(self, newer: SelfHarmScreening | None) -> SelfHarmScreening | None:
        """Новый скрининг; `unknown` — тоже неясность, известный ответ он не перекрывает."""
        if newer not in {None, SelfHarmScreening.UNKNOWN}:
            return newer
        return self.self_harm if self.self_harm is not None else newer

    def _normalize(self) -> None:
        self._normalize_evidence()
        self._normalize_goal()
        self._normalize_refused()
        self._normalize_confidence()

    def _normalize_evidence(self) -> None:
        """Отбрасывает повторы терминов и цитат; остаётся первое упоминание."""
        self._set("manifestations", _unique_by_term(self.manifestations))
        self._set("stressors", _unique_by_term(self.stressors))
        self._set("unrecognized", _unique_quotes(self.unrecognized))

    def _normalize_goal(self) -> None:
        """Обрезает пробелы; пустая цель становится `None`."""
        if self.goal is not None:
            self._set("goal", self.goal.strip() or None)

    def _normalize_refused(self) -> None:
        """Снимает отказ от известных сведений; отказ от скрининга даёт `unknown`."""
        self._set("refused", frozenset(kind for kind in self.refused if not self.is_known(kind)))
        if FactKind.SELF_HARM in self.refused and self.self_harm is None:
            self._set("self_harm", SelfHarmScreening.UNKNOWN)

    def _normalize_confidence(self) -> None:
        """Отбрасывает уверенность в неизвестных значениях."""
        self._set(
            "confidence",
            MappingProxyType(
                {kind: value for kind, value in self.confidence.items() if self.is_known(kind)},
            ),
        )

    def _validate(self) -> None:
        self._validate_goal()
        self._validate_confidence()

    def _validate_goal(self) -> None:
        if self.goal is not None and len(self.goal) > self._MAX_GOAL_LENGTH:
            raise ValidationError(
                field=self._FIELD_NAME,
                reason=f"goal must not exceed {self._MAX_GOAL_LENGTH} characters",
            )

    def _validate_confidence(self) -> None:
        for kind, value in self.confidence.items():
            if kind not in ESTIMATED_FACTS:
                raise ValidationError(
                    field=self._FIELD_NAME,
                    reason=f"'{kind}' cannot have a confidence",
                )
            if not 0 < value <= 1:
                raise ValidationError(
                    field=self._FIELD_NAME,
                    reason=f"confidence of '{kind}' must be in (0, 1]",
                )


def _newer[T](old: T | None, new: T | None) -> T | None:
    """Новое значение, если оно известно, иначе старое."""
    return new if new is not None else old


def _unique_by_term(items: Iterable[Evidence]) -> tuple[Evidence, ...]:
    """Признаки без повторов по термину; цитата берётся из первого."""
    seen: dict[TermId, Evidence] = {}
    for evidence in items:
        seen.setdefault(evidence.term, evidence)
    return tuple(seen.values())


def _unique_quotes(quotes: Iterable[str]) -> tuple[str, ...]:
    """Цитаты без повторов и пустых, в исходном порядке."""
    unique: dict[str, Any] = dict.fromkeys(quote.strip() for quote in quotes)
    return tuple(quote for quote in unique if quote)
