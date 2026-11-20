from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from re import Pattern
from types import MappingProxyType
from typing import Final, override

from pydantic import field_validator

from anamnesis.application.errors.knowledge import UnsupportedLanguageError
from anamnesis.application.interfaces.safety.reply_guard import (
    IReplyGuard,
    ReplyViolation,
    ViolationKind,
)
from anamnesis.domain.enums.recommendation import UrgencyLevel
from anamnesis.domain.types import LanguageCode
from anamnesis.infrastructure.filesystem.yaml_reader import read_yaml
from anamnesis.infrastructure.text.language import LanguageProfile, LanguageProfiles, Token
from anamnesis.infrastructure.text.patterns import PatternFile, PatternMatcher


_GUARD_FILE: Final[str] = "guard.yaml"

_LOWEST_LEVEL: Final[UrgencyLevel] = UrgencyLevel.L0
"""При «недостаточно данных» недопустимо только утверждать, что срочности нет."""


class GuardFile(PatternFile):
    """`resources/<язык>/guard.yaml`: шаблоны проверки ответов системы.

    Attributes:
        patterns: Шаблоны по видам нарушений.
        codes: Регулярные выражения кодов МКБ: код — тоже утверждение диагноза.
        levels: Утверждения об уровне срочности по уровням `L0`–`L3`.
    """

    patterns: Mapping[ViolationKind, tuple[str, ...]]
    codes: tuple[Pattern[str], ...]
    levels: Mapping[UrgencyLevel, tuple[str, ...]]

    @field_validator("levels", mode="before")
    @classmethod
    def _levels_by_name(cls, levels: object) -> object:
        """Уровни в файле названы именами `L0`–`L3`, а не числами."""
        if not isinstance(levels, Mapping):
            return levels
        names: frozenset[str] = frozenset(level.name for level in UrgencyLevel)
        unknown: list[str] = sorted(str(name) for name in levels if name not in names)
        if unknown:
            raise ValueError(f"Unknown urgency levels {unknown}")
        return {UrgencyLevel[name]: patterns for name, patterns in levels.items()}


@dataclass(frozen=True, slots=True)
class _Patterns:
    """Шаблоны одного языка: нарушения, коды МКБ и утверждения об уровне."""

    profile: LanguageProfile
    violations: PatternMatcher[ViolationKind]
    levels: PatternMatcher[UrgencyLevel]
    codes: tuple[Pattern[str], ...]


class LexiconReplyGuard(IReplyGuard):
    """Проверяет ответ системы по шаблонам `guard.yaml`.

    Уровень считается расходящимся, если ответ утверждает уровень, отличный от
    вычисленного правилами; при «недостаточно данных» — только если ответ
    утверждает, что срочности нет.
    """

    def __init__(self, patterns: Mapping[LanguageCode, _Patterns]) -> None:
        self._patterns: Mapping[LanguageCode, _Patterns] = MappingProxyType(dict(patterns))

    @classmethod
    def load(cls, root: Path, profiles: LanguageProfiles) -> "LexiconReplyGuard":
        patterns: dict[LanguageCode, _Patterns] = {}

        for language in profiles.languages:
            profile: LanguageProfile = profiles.get(language)
            document: GuardFile = read_yaml(root / language / _GUARD_FILE, GuardFile)
            patterns[language] = _Patterns(
                profile=profile,
                violations=PatternMatcher(
                    document.patterns,
                    profile=profile,
                    negations=document.negations,
                    negation_window=document.negation_window,
                ),
                levels=PatternMatcher(
                    document.levels,
                    profile=profile,
                    negations=document.negations,
                    negation_window=document.negation_window,
                ),
                codes=document.codes,
            )

        return cls(patterns)

    @staticmethod
    def _phrases(
        text: str,
        tokens: tuple[Token, ...],
        patterns: _Patterns,
    ) -> list[ReplyViolation]:
        """Нарушения по шаблонам: диагнозы, лекарства, обещания, обесценивание."""
        violations: list[ReplyViolation] = [
            ReplyViolation(kind=match.key, quote=_quote(text, tokens, match.first, match.last))
            for match in patterns.violations.find(tokens)
        ]
        return violations

    @staticmethod
    def _codes(text: str, patterns: _Patterns) -> list[ReplyViolation]:
        """Коды МКБ — тоже утверждение диагноза."""
        violations: list[ReplyViolation] = [
            ReplyViolation(kind=ViolationKind.DIAGNOSIS, quote=code.group())
            for pattern in patterns.codes
            for code in pattern.finditer(text)
        ]
        return violations

    @staticmethod
    def _levels(
        text: str,
        tokens: tuple[Token, ...],
        patterns: _Patterns,
        level: UrgencyLevel | None,
    ) -> list[ReplyViolation]:
        """Утверждения об уровне, расходящиеся с вычисленным правилами."""
        violations: list[ReplyViolation] = [
            ReplyViolation(
                kind=ViolationKind.LEVEL_MISMATCH,
                quote=_quote(text, tokens, match.first, match.last),
            )
            for match in patterns.levels.find(tokens)
            if _mismatch(claimed=match.key, computed=level)
        ]
        return violations

    @override
    async def check(
        self,
        text: str,
        language: LanguageCode,
        level: UrgencyLevel | None,
    ) -> tuple[ReplyViolation, ...]:
        patterns: _Patterns | None = self._patterns.get(language)
        if patterns is None:
            raise UnsupportedLanguageError(language=language)

        tokens: tuple[Token, ...] = patterns.profile.tokenize(text)

        violations: dict[ReplyViolation, None] = dict.fromkeys(
            (
                *self._phrases(text, tokens, patterns),
                *self._codes(text, patterns),
                *self._levels(text, tokens, patterns, level),
            ),
        )
        return tuple(violations)


def _mismatch(*, claimed: UrgencyLevel, computed: UrgencyLevel | None) -> bool:
    """Утверждённый в ответе уровень расходится с вычисленным правилами."""
    if computed is None:
        return claimed is _LOWEST_LEVEL
    return claimed is not computed


def _quote(text: str, tokens: tuple[Token, ...], first: int, last: int) -> str:
    """Фрагмент исходного текста от первого до последнего слова совпадения."""
    return text[tokens[first].start : tokens[last].end]
