from dataclasses import dataclass
import re
from typing import Final, Protocol

import snowballstemmer


_WORD: Final[re.Pattern[str]] = re.compile(r"\w+")
"""Слово текста."""

_CLAUSE_BREAK: Final[re.Pattern[str]] = re.compile(r"[,;:—–()]")
"""Граница части предложения между словами."""

_SENTENCE_BREAK: Final[re.Pattern[str]] = re.compile(r"[.!?\n]")
"""Граница предложения между словами."""


class Stemmer(Protocol):
    def stemWord(self, word: str) -> str: ...  # noqa: N802


@dataclass(frozen=True, slots=True)
class Token:
    """Слово текста: основа, место в тексте и границы перед ним.

    Attributes:
        word: Слово в нижнем регистре, `ё` заменена на `е`.
        stem: Основа слова.
        start: Начало слова в исходном тексте.
        end: Конец слова в исходном тексте.
        clause_break: Перед словом граница части предложения или предложения.
        sentence_break: Перед словом граница предложения.
    """

    word: str
    stem: str
    start: int
    end: int
    clause_break: bool
    sentence_break: bool


def make_stemmer(language: str) -> Stemmer:
    """Стеммер Snowball по названию языка: `russian`, `english` и другие."""
    stemmer: Stemmer = snowballstemmer.stemmer(language)
    return stemmer


def tokenize(text: str, stemmer: Stemmer) -> tuple[Token, ...]:
    """Слова текста с основами, позициями и границами частей предложения."""
    tokens: list[Token] = []
    previous_end: int = 0
    for match in _WORD.finditer(text):
        word: str = match.group().lower().replace("ё", "е")
        gap: str = text[previous_end : match.start()]
        sentence_break: bool = not tokens or bool(_SENTENCE_BREAK.search(gap))
        tokens.append(
            Token(
                word=word,
                stem=stemmer.stemWord(word),
                start=match.start(),
                end=match.end(),
                clause_break=sentence_break or bool(_CLAUSE_BREAK.search(gap)),
                sentence_break=sentence_break,
            ),
        )
        previous_end = match.end()
    return tuple(tokens)
