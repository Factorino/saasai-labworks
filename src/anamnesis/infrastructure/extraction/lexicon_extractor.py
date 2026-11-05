from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final, override

from anamnesis.application.interfaces.extraction.fact_extractor import IFactExtractor
from anamnesis.domain.types import LanguageCode, TermId
from anamnesis.domain.value_objects.case_facts import CaseFacts
from anamnesis.domain.value_objects.evidence import Evidence
from anamnesis.infrastructure.localization.locale import Lexicon, Locale
from anamnesis.infrastructure.text.tokens import Stemmer, Token, make_stemmer, tokenize


_NEGATION: Final[str] = "не"
"""Отрицание перед фразой отменяет находку: «мне не грустно»."""


@dataclass(frozen=True, slots=True)
class _Phrase:
    """Фраза словаря как последовательность основ."""

    term: TermId
    stems: tuple[str, ...]
    negative: bool


@dataclass(frozen=True, slots=True)
class _Index:
    """Словарь одного языка: фразы по основе первого слова."""

    stemmer: Stemmer
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
        tokens: tuple[Token, ...] = tokenize(text, index.stemmer)
        return CaseFacts(
            manifestations=_find(text, tokens, index.manifestations),
            stressors=_find(text, tokens, index.stressors),
        )


def _build_index(lexicon: Lexicon) -> _Index:
    stemmer: Stemmer = make_stemmer(lexicon.stemmer)
    return _Index(
        stemmer=stemmer,
        manifestations=_index_phrases(lexicon.manifestations, stemmer),
        stressors=_index_phrases(lexicon.stressors, stemmer),
    )


def _index_phrases(
    terms: Mapping[TermId, tuple[str, ...]],
    stemmer: Stemmer,
) -> Mapping[str, tuple[_Phrase, ...]]:
    """Группирует фразы по основе первого слова, длинные фразы — раньше."""
    index: dict[str, list[_Phrase]] = {}
    for term, phrases in terms.items():
        for phrase in phrases:
            tokens: tuple[Token, ...] = tokenize(phrase, stemmer)
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


def _find(
    text: str,
    tokens: tuple[Token, ...],
    index: Mapping[str, tuple[_Phrase, ...]],
) -> tuple[Evidence, ...]:
    """Находки по порядку в тексте; цитата — совпавший фрагмент реплики."""
    found: list[Evidence] = []
    for position, token in enumerate(tokens):
        for phrase in index.get(token.stem, ()):
            if _matches(tokens, position, phrase):
                last: Token = tokens[position + len(phrase.stems) - 1]
                found.append(Evidence(term=phrase.term, quote=text[token.start : last.end]))
    return tuple(found)


def _matches(tokens: tuple[Token, ...], position: int, phrase: _Phrase) -> bool:
    window: tuple[Token, ...] = tokens[position : position + len(phrase.stems)]
    if tuple(token.stem for token in window) != phrase.stems:
        return False
    negated: bool = position > 0 and tokens[position - 1].word == _NEGATION
    return phrase.negative or not negated
