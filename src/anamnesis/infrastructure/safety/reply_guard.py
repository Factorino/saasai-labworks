from collections.abc import Mapping
from dataclasses import dataclass
import re
from types import MappingProxyType
from typing import Final, override

from anamnesis.application.interfaces.safety.reply_guard import IReplyGuard
from anamnesis.domain.enums.urgency_level import UrgencyLevel
from anamnesis.domain.enums.violation_kind import ViolationKind
from anamnesis.domain.types import LanguageCode
from anamnesis.domain.value_objects.reply_violation import ReplyViolation
from anamnesis.infrastructure.localization.locale import Guard, Locale
from anamnesis.infrastructure.text.patterns import PatternMatcher
from anamnesis.infrastructure.text.tokens import Stemmer, Token, make_stemmer, tokenize


_LOWEST_LEVEL: Final[UrgencyLevel] = UrgencyLevel.L0
"""При «недостаточно данных» недопустимо только утверждать, что срочности нет."""


@dataclass(frozen=True, slots=True)
class _Index:
    """Шаблоны одного языка: нарушения, коды МКБ и утверждения об уровне."""

    violations: PatternMatcher[ViolationKind]
    levels: PatternMatcher[UrgencyLevel]
    codes: tuple[re.Pattern[str], ...]


class LexiconReplyGuard(IReplyGuard):
    """Проверяет ответ системы по шаблонам `guard.yaml` (SPEC §6.2).

    Уровень считается расходящимся, если ответ утверждает уровень, отличный от
    вычисленного правилами; при «недостаточно данных» — только если ответ
    утверждает, что срочности нет.
    """

    def __init__(self, locales: Mapping[LanguageCode, Locale]) -> None:
        self._indexes: Mapping[LanguageCode, _Index] = MappingProxyType(
            {language: _build_index(locale.guard) for language, locale in locales.items()},
        )

    @override
    async def check(
        self,
        text: str,
        language: LanguageCode,
        level: UrgencyLevel | None,
    ) -> tuple[ReplyViolation, ...]:
        index: _Index = self._indexes[language]
        tokens: tuple[Token, ...] = tokenize(text, index.violations.stemmer)
        violations: dict[ReplyViolation, None] = dict.fromkeys(
            (
                *_phrases(text, tokens, index),
                *_codes(text, index),
                *_levels(text, tokens, index, level),
            ),
        )
        return tuple(violations)


def _phrases(text: str, tokens: tuple[Token, ...], index: _Index) -> list[ReplyViolation]:
    """Нарушения по шаблонам: диагнозы, лекарства, обещания, обесценивание."""
    return [
        ReplyViolation(kind=match.key, quote=_quote(text, tokens, match.first, match.last))
        for match in index.violations.find(tokens)
    ]


def _codes(text: str, index: _Index) -> list[ReplyViolation]:
    """Коды МКБ — тоже утверждение диагноза."""
    return [
        ReplyViolation(kind=ViolationKind.DIAGNOSIS, quote=code.group())
        for pattern in index.codes
        for code in pattern.finditer(text)
    ]


def _levels(
    text: str,
    tokens: tuple[Token, ...],
    index: _Index,
    level: UrgencyLevel | None,
) -> list[ReplyViolation]:
    """Утверждения об уровне, расходящиеся с вычисленным правилами."""
    return [
        ReplyViolation(
            kind=ViolationKind.LEVEL_MISMATCH,
            quote=_quote(text, tokens, match.first, match.last),
        )
        for match in index.levels.find(tokens)
        if _mismatch(claimed=match.key, computed=level)
    ]


def _build_index(guard: Guard) -> _Index:
    stemmer: Stemmer = make_stemmer(guard.stemmer)
    return _Index(
        violations=PatternMatcher(guard.patterns, stemmer=stemmer, negations=guard.negations),
        levels=PatternMatcher(
            {UrgencyLevel[name]: texts for name, texts in guard.levels.items()},
            stemmer=stemmer,
            negations=guard.negations,
        ),
        codes=tuple(re.compile(code) for code in guard.codes),
    )


def _mismatch(*, claimed: UrgencyLevel, computed: UrgencyLevel | None) -> bool:
    if computed is None:
        return claimed is _LOWEST_LEVEL
    return claimed is not computed


def _quote(text: str, tokens: tuple[Token, ...], first: int, last: int) -> str:
    return text[tokens[first].start : tokens[last].end]
