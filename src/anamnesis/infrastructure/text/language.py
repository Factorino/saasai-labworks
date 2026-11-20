from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
import re
from types import MappingProxyType
from typing import Final, Protocol

from pydantic import Field
import snowballstemmer

from anamnesis.application.errors.knowledge import UnsupportedLanguageError
from anamnesis.domain.types import LanguageCode
from anamnesis.infrastructure.filesystem.yaml_reader import YamlFile, read_yaml


_WORD: Final[re.Pattern[str]] = re.compile(r"\w+")
"""Слово текста."""

_CLAUSE_BREAK: Final[re.Pattern[str]] = re.compile(r"[,;:—–()]")
"""Граница части предложения между словами."""

_SENTENCE_BREAK: Final[re.Pattern[str]] = re.compile(r"[.!?\n]")
"""Граница предложения между словами."""

_LANGUAGE_FILE: Final[str] = "language.yaml"


class Stemmer(Protocol):
    def stemWord(self, word: str) -> str: ...  # noqa: N802


@dataclass(frozen=True, slots=True)
class Token:
    """Слово текста: основа, место в тексте и границы перед ним.

    Attributes:
        word: Слово в нижнем регистре после замены букв.
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


class LanguageFile(YamlFile):
    """`resources/<язык>/language.yaml`: общее для языка.

    Attributes:
        stemmer: Название стеммера Snowball: `russian`, `english` и другие.
        letters: Замена букв перед сравнением: `ё` → `е`.
        max_gap: Сколько слов можно пропустить на месте `...` в шаблоне.
    """

    stemmer: str
    letters: Mapping[str, str] = Field(default_factory=dict)
    max_gap: int = Field(ge=0)


class LanguageProfile:
    """Как слова языка приводятся к сравнимому виду: регистр, замена букв, основа."""

    def __init__(self, *, stemmer: Stemmer, letters: Mapping[str, str], max_gap: int) -> None:
        self._stemmer: Stemmer = stemmer
        self._letters: dict[int, str] = str.maketrans(dict(letters))
        self._max_gap: int = max_gap

    @classmethod
    def from_file(cls, document: LanguageFile) -> "LanguageProfile":
        """Профиль по файлу языка."""
        stemmer: Stemmer = snowballstemmer.stemmer(document.stemmer)
        return cls(stemmer=stemmer, letters=document.letters, max_gap=document.max_gap)

    @property
    def max_gap(self) -> int:
        """Сколько слов можно пропустить на месте `...` в шаблоне."""
        return self._max_gap

    def normalize(self, word: str) -> str:
        """Слово в нижнем регистре после замены букв."""
        return word.lower().translate(self._letters)

    def stem(self, word: str) -> str:
        """Основа слова после приведения к нижнему регистру и замены букв."""
        return self._stemmer.stemWord(self.normalize(word))

    def tokenize(self, text: str) -> tuple[Token, ...]:
        """Слова текста с основами, позициями и границами частей предложения."""
        tokens: list[Token] = []
        previous_end: int = 0

        for match in _WORD.finditer(text):
            word: str = self.normalize(match.group())
            gap: str = text[previous_end : match.start()]
            sentence_break: bool = not tokens or bool(_SENTENCE_BREAK.search(gap))
            tokens.append(
                Token(
                    word=word,
                    stem=self._stemmer.stemWord(word),
                    start=match.start(),
                    end=match.end(),
                    clause_break=sentence_break or bool(_CLAUSE_BREAK.search(gap)),
                    sentence_break=sentence_break,
                ),
            )
            previous_end = match.end()

        return tuple(tokens)


class LanguageProfiles:
    """Профили языков, загруженные при запуске."""

    def __init__(self, profiles: Mapping[LanguageCode, LanguageProfile]) -> None:
        self._profiles: Mapping[LanguageCode, LanguageProfile] = MappingProxyType(dict(profiles))

    @classmethod
    def load(cls, root: Path, languages: Iterable[LanguageCode]) -> "LanguageProfiles":
        profiles: dict[LanguageCode, LanguageProfile] = {
            language: LanguageProfile.from_file(
                read_yaml(root / language / _LANGUAGE_FILE, LanguageFile)
            )
            for language in languages
        }
        return cls(profiles)

    @property
    def languages(self) -> tuple[LanguageCode, ...]:
        return tuple(self._profiles)

    def get(self, language: LanguageCode) -> LanguageProfile:
        profile: LanguageProfile | None = self._profiles.get(language)
        if profile is None:
            raise UnsupportedLanguageError(language=language)
        return profile
