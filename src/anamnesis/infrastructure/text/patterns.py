from collections.abc import Hashable, Iterable, Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final

from anamnesis.infrastructure.text.tokens import Stemmer, Token, tokenize


GAP: Final[str] = "..."
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
class _Pattern[KeyT: Hashable]:
    """Шаблон с ключом; `negative` — шаблон сам начинается с отрицания."""

    key: KeyT
    elements: tuple[_Element, ...]
    negative: bool


@dataclass(frozen=True, slots=True)
class PatternMatch[KeyT: Hashable]:
    """Совпадение шаблона: ключ и номера первого и последнего слова в тексте.

    Attributes:
        key: Ключ шаблона: категория, вид нарушения, уровень.
        first: Номер первого совпавшего слова.
        last: Номер последнего совпавшего слова.
    """

    key: KeyT
    first: int
    last: int

    def contains(self, other: "PatternMatch[KeyT]") -> bool:
        """Другое совпадение с тем же ключом лежит внутри этого и короче его."""
        return (
            self.key == other.key
            and self.first <= other.first
            and other.last <= self.last
            and (self.first, self.last) != (other.first, other.last)
        )


class PatternMatcher[KeyT: Hashable]:
    """Ищет в тексте шаблоны вида «слово ... слово» по основам слов.

    Шаблон — слова через пробел, `...` разрешает пропустить до трёх слов, но не
    границу предложения. Отрицание в трёх словах перед находкой (до запятой)
    отменяет её, если шаблон сам не начинается с отрицания. Из вложенных
    совпадений с одним ключом остаётся самое длинное.
    """

    def __init__(
        self,
        patterns: Mapping[KeyT, Iterable[str]],
        *,
        stemmer: Stemmer,
        negations: Iterable[str],
    ) -> None:
        self._stemmer: Stemmer = stemmer
        self._negations: frozenset[str] = frozenset(negations)
        index: dict[str, list[_Pattern[KeyT]]] = {}
        for key, texts in patterns.items():
            for text in texts:
                pattern: _Pattern[KeyT] = self._compile(key, text)
                index.setdefault(pattern.elements[0].stem, []).append(pattern)
        self._index: Mapping[str, tuple[_Pattern[KeyT], ...]] = MappingProxyType(
            {stem: tuple(items) for stem, items in index.items()},
        )

    @property
    def stemmer(self) -> Stemmer:
        return self._stemmer

    def find(self, tokens: tuple[Token, ...]) -> tuple[PatternMatch[KeyT], ...]:
        """Совпадения по порядку в тексте, без отрицаний и вложенных повторов."""
        found: list[PatternMatch[KeyT]] = []
        for position, token in enumerate(tokens):
            for pattern in self._index.get(token.stem, ()):
                last: int | None = _match(tokens, position, pattern)
                if last is None or (not pattern.negative and self._negated(tokens, position)):
                    continue
                found.append(PatternMatch(key=pattern.key, first=position, last=last))
        return tuple(
            match
            for match in found
            if not any(other.contains(match) for other in found if other is not match)
        )

    def _compile(self, key: KeyT, text: str) -> _Pattern[KeyT]:
        elements: list[_Element] = []
        gap: bool = False
        for part in text.split():
            if part == GAP:
                gap = True
                continue
            for token in tokenize(part, self._stemmer):
                elements.append(_Element(stem=token.stem, gap=gap))
                gap = False
        first_word: str = text.split(maxsplit=1)[0].lower()
        return _Pattern(
            key=key,
            elements=tuple(elements),
            negative=first_word in self._negations,
        )

    def _negated(self, tokens: tuple[Token, ...], start: int) -> bool:
        """Есть ли отрицание перед находкой в той же части предложения."""
        position: int = start
        while position > 0 and start - position < _NEGATION_WINDOW:
            if tokens[position].clause_break:
                return False
            position -= 1
            if tokens[position].word in self._negations:
                return True
        return False


def _match[KeyT: Hashable](
    tokens: tuple[Token, ...],
    start: int,
    pattern: _Pattern[KeyT],
) -> int | None:
    """Номер последнего слова совпадения или `None`; совпадение не выходит за предложение."""
    position: int = start
    for element in pattern.elements[1:]:
        limit: int = position + 1 + (_MAX_GAP if element.gap else 0)
        found: int | None = None
        for candidate in range(position + 1, min(limit + 1, len(tokens))):
            if tokens[candidate].sentence_break:
                break
            if tokens[candidate].stem == element.stem:
                found = candidate
                break
        if found is None:
            return None
        position = found
    return position
