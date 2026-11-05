from collections.abc import Mapping
from dataclasses import dataclass
import re
from types import MappingProxyType
from typing import Final, Protocol, override

import snowballstemmer

from anamnesis.application.interfaces.extraction.fact_extractor import IFactExtractor
from anamnesis.domain.types import LanguageCode, TermId
from anamnesis.domain.value_objects.case_facts import CaseFacts
from anamnesis.domain.value_objects.evidence import Evidence
from anamnesis.infrastructure.localization.locale import Lexicon, Locale


_WORD: Final[re.Pattern[str]] = re.compile(r"\w+")
"""Слово реплики или фразы словаря."""

_NEGATION: Final[str] = "не"
"""Отрицание перед фразой отменяет находку: «мне не грустно»."""


class _Stemmer(Protocol):
    def stemWord(self, word: str) -> str: ...  # noqa: N802


@dataclass(frozen=True, slots=True)
class _Token:
    """Слово реплики: основа и место в исходном тексте."""

    word: str
    stem: str
    start: int
    end: int


@dataclass(frozen=True, slots=True)
class _Phrase:
    """Фраза словаря как последовательность основ."""

    term: TermId
    stems: tuple[str, ...]
    negative: bool


@dataclass(frozen=True, slots=True)
class _Index:
    """Словарь одного языка: фразы по основе первого слова."""

    stemmer: _Stemmer
    manifestations: Mapping[str, tuple[_Phrase, ...]]
    stressors: Mapping[str, tuple[_Phrase, ...]]


class LexiconFactExtractor(IFactExtractor):
    """Находит термины онтологии по фразам словаря `lexicon.yaml`.

    Слова сравниваются по основам (стеммер Snowball), поэтому форма слова в
    реплике может отличаться от фразы словаря. Фраза засчитывается, если её
    основы идут в реплике подряд и перед ней нет отрицания.
    """

    def __init__(self, locales: Mapping[LanguageCode, Locale]) -> None:
        self._indexes: Mapping[LanguageCode, _Index] = MappingProxyType(
            {language: _build_index(locale.lexicon) for language, locale in locales.items()},
        )

    @override
    async def extract(self, text: str, language: LanguageCode) -> CaseFacts:
        index: _Index = self._indexes[language]
        tokens: tuple[_Token, ...] = _tokenize(text, index.stemmer)
        return CaseFacts(
            manifestations=_find(text, tokens, index.manifestations),
            stressors=_find(text, tokens, index.stressors),
        )


def _build_index(lexicon: Lexicon) -> _Index:
    stemmer: _Stemmer = snowballstemmer.stemmer(lexicon.stemmer)
    return _Index(
        stemmer=stemmer,
        manifestations=_index_phrases(lexicon.manifestations, stemmer),
        stressors=_index_phrases(lexicon.stressors, stemmer),
    )


def _index_phrases(
    terms: Mapping[TermId, tuple[str, ...]],
    stemmer: _Stemmer,
) -> Mapping[str, tuple[_Phrase, ...]]:
    """Группирует фразы по основе первого слова, длинные фразы — раньше."""
    index: dict[str, list[_Phrase]] = {}
    for term, phrases in terms.items():
        for phrase in phrases:
            tokens: tuple[_Token, ...] = _tokenize(phrase, stemmer)
            if not tokens:
                continue
            entry = _Phrase(
                term=term,
                stems=tuple(token.stem for token in tokens),
                negative=tokens[0].word == _NEGATION,
            )
            index.setdefault(entry.stems[0], []).append(entry)
    return MappingProxyType(
        {
            stem: tuple(sorted(entries, key=lambda entry: -len(entry.stems)))
            for stem, entries in index.items()
        },
    )


def _tokenize(text: str, stemmer: _Stemmer) -> tuple[_Token, ...]:
    """Слова в нижнем регистре, `ё` как `е`, с основами и позициями."""
    tokens: list[_Token] = []
    for match in _WORD.finditer(text):
        word: str = match.group().lower().replace("ё", "е")
        tokens.append(
            _Token(word=word, stem=stemmer.stemWord(word), start=match.start(), end=match.end()),
        )
    return tuple(tokens)


def _find(
    text: str,
    tokens: tuple[_Token, ...],
    index: Mapping[str, tuple[_Phrase, ...]],
) -> tuple[Evidence, ...]:
    """Находки по порядку в тексте; цитата — совпавший фрагмент реплики."""
    found: list[Evidence] = []
    for position, token in enumerate(tokens):
        for phrase in index.get(token.stem, ()):
            if _matches(tokens, position, phrase):
                last: _Token = tokens[position + len(phrase.stems) - 1]
                found.append(Evidence(term=phrase.term, quote=text[token.start : last.end]))
    return tuple(found)


def _matches(tokens: tuple[_Token, ...], position: int, phrase: _Phrase) -> bool:
    window: tuple[_Token, ...] = tokens[position : position + len(phrase.stems)]
    if tuple(token.stem for token in window) != phrase.stems:
        return False
    negated: bool = position > 0 and tokens[position - 1].word == _NEGATION
    return phrase.negative or not negated
