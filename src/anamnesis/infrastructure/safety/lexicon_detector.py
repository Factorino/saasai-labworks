from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final, override

from anamnesis.application.interfaces.safety.crisis_detector import ICrisisDetector
from anamnesis.domain.enums.crisis_category import CrisisCategory
from anamnesis.domain.types import LanguageCode
from anamnesis.domain.value_objects.crisis_signal import CrisisSignal
from anamnesis.infrastructure.localization.locale import Crisis, Locale
from anamnesis.infrastructure.text.tokens import Stemmer, Token, make_stemmer, tokenize


_GAP: Final[str] = "..."
"""Пропуск в шаблоне: между соседними словами могут стоять другие."""

_MAX_GAP: Final[int] = 3
"""Сколько слов можно пропустить на месте `...`."""

_NEGATION_WINDOW: Final[int] = 3
"""Сколько слов перед находкой проверяется на отрицание."""


@dataclass(frozen=True, slots=True)
class _Element:
    """Слово шаблона; `gap` — перед ним можно пропустить слова."""

    stem: str
    gap: bool


@dataclass(frozen=True, slots=True)
class _Pattern:
    """Шаблон категории; `negative` — шаблон сам начинается с отрицания."""

    category: CrisisCategory
    elements: tuple[_Element, ...]
    negative: bool


@dataclass(frozen=True, slots=True)
class _Finding:
    """Совпадение шаблона: категория и место в тексте."""

    category: CrisisCategory
    start: int
    end: int

    def contains(self, other: "_Finding") -> bool:
        """Другая находка той же категории лежит внутри этой и короче её."""
        return (
            self.category is other.category
            and self.start <= other.start
            and other.end <= self.end
            and (self.start, self.end) != (other.start, other.end)
        )


@dataclass(frozen=True, slots=True)
class _Index:
    """Шаблоны одного языка по основе первого слова и слова контекста."""

    stemmer: Stemmer
    patterns: Mapping[str, tuple[_Pattern, ...]]
    negations: frozenset[str]
    first_person: frozenset[str]
    others: frozenset[str]


class LexiconCrisisDetector(ICrisisDetector):
    """Находит кризисные формулировки по шаблонам `crisis.yaml`."""

    def __init__(self, locales: Mapping[LanguageCode, Locale]) -> None:
        self._indexes: Mapping[LanguageCode, _Index] = MappingProxyType(
            {language: _build_index(locale.crisis) for language, locale in locales.items()},
        )

    @override
    async def detect(self, text: str, language: LanguageCode) -> tuple[CrisisSignal, ...]:
        index: _Index = self._indexes[language]
        tokens: tuple[Token, ...] = tokenize(text, index.stemmer)
        found: list[_Finding] = []
        for position, token in enumerate(tokens):
            for pattern in index.patterns.get(token.stem, ()):
                end: int | None = _match(tokens, position, pattern)
                if end is None or (not pattern.negative and _negated(tokens, position, index)):
                    continue
                category: CrisisCategory = (
                    CrisisCategory.OTHER_PERSON
                    if _about_other(tokens, position, index)
                    else pattern.category
                )
                found.append(_Finding(category=category, start=token.start, end=tokens[end].end))
        signals: dict[CrisisSignal, None] = {
            CrisisSignal(category=item.category, quote=text[item.start : item.end]): None
            for item in found
            if not any(other.contains(item) for other in found if other is not item)
        }
        return tuple(signals)


def _build_index(crisis: Crisis) -> _Index:
    stemmer: Stemmer = make_stemmer(crisis.stemmer)
    negations: frozenset[str] = frozenset(crisis.negations)
    patterns: dict[str, list[_Pattern]] = {}
    for category, texts in crisis.patterns.items():
        for text in texts:
            pattern: _Pattern = _compile(category, text, stemmer, negations)
            patterns.setdefault(pattern.elements[0].stem, []).append(pattern)
    return _Index(
        stemmer=stemmer,
        patterns=MappingProxyType({stem: tuple(items) for stem, items in patterns.items()}),
        negations=negations,
        first_person=frozenset(crisis.first_person),
        others=frozenset(stemmer.stemWord(word) for word in crisis.others),
    )


def _compile(
    category: CrisisCategory,
    text: str,
    stemmer: Stemmer,
    negations: frozenset[str],
) -> _Pattern:
    """Шаблон из строки словаря: основы слов и места пропусков."""
    elements: list[_Element] = []
    gap: bool = False
    for part in text.split():
        if part == _GAP:
            gap = True
            continue
        for token in tokenize(part, stemmer):
            elements.append(_Element(stem=token.stem, gap=gap))
            gap = False
    first_word: str = text.split(maxsplit=1)[0].lower()
    return _Pattern(category=category, elements=tuple(elements), negative=first_word in negations)


def _match(tokens: tuple[Token, ...], start: int, pattern: _Pattern) -> int | None:
    """Позиция последнего слова совпадения или `None`; совпадение не выходит за предложение."""
    position: int = start
    for element in pattern.elements[1:]:
        limit: int = position + 1 + (_MAX_GAP if element.gap else 0)
        candidates = range(position + 1, min(limit + 1, len(tokens)))
        found: int | None = None
        for candidate in candidates:
            if tokens[candidate].sentence_break:
                break
            if tokens[candidate].stem == element.stem:
                found = candidate
                break
        if found is None:
            return None
        position = found
    return position


def _negated(tokens: tuple[Token, ...], start: int, index: _Index) -> bool:
    """Есть ли отрицание перед находкой в той же части предложения."""
    position: int = start
    while position > 0 and start - position < _NEGATION_WINDOW:
        if tokens[position].clause_break:
            return False
        position -= 1
        if tokens[position].word in index.negations:
            return True
    return False


def _about_other(tokens: tuple[Token, ...], start: int, index: _Index) -> bool:
    """Ближайшее действующее лицо перед находкой в предложении — другой человек."""
    position: int = start
    while position > 0 and not tokens[position].sentence_break:
        position -= 1
        token: Token = tokens[position]
        if token.word in index.first_person:
            return False
        if token.stem in index.others:
            return True
    return False
