from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Final, override

from anamnesis.application.errors.knowledge import UnsupportedLanguageError
from anamnesis.application.interfaces.extraction.fact_extractor import IFactExtractor
from anamnesis.domain.types import LanguageCode, TermId
from anamnesis.domain.value_objects.case_facts import CaseFacts
from anamnesis.domain.value_objects.evidence import Evidence
from anamnesis.infrastructure.filesystem.yaml_reader import read_yaml
from anamnesis.infrastructure.text.language import LanguageProfile, LanguageProfiles, Token
from anamnesis.infrastructure.text.patterns import PatternFile


_LEXICON_FILE: Final[str] = "lexicon.yaml"

type _PhraseIndex = Mapping[str, tuple[_Phrase, ...]]
"""Фразы по основе первого слова, длинные — раньше."""


class LexiconFile(PatternFile):
    """`resources/<язык>/lexicon.yaml`: фразы, по которым находятся термины онтологии.

    Attributes:
        manifestations: Фразы проявлений по терминам.
        stressors: Фразы стрессоров по терминам.
    """

    manifestations: Mapping[TermId, tuple[str, ...]]
    stressors: Mapping[TermId, tuple[str, ...]]


@dataclass(frozen=True, slots=True)
class _Phrase:
    """Фраза словаря как последовательность основ; `negative` — начинается с отрицания."""

    term: TermId
    stems: tuple[str, ...]
    negative: bool


@dataclass(frozen=True, slots=True)
class _Lexicon:
    """Словарь одного языка, готовый к поиску."""

    profile: LanguageProfile
    negations: frozenset[str]
    negation_window: int
    manifestations: _PhraseIndex
    stressors: _PhraseIndex


class LexiconFactExtractor(IFactExtractor):
    """Находит термины онтологии по фразам словаря `lexicon.yaml`.

    Слова сравниваются по основам, поэтому форма слова в реплике может
    отличаться от фразы словаря. Фраза засчитывается, если её основы идут в
    реплике подряд и в `negation_window` словах перед ней нет отрицания.
    """

    def __init__(self, lexicons: Mapping[LanguageCode, _Lexicon]) -> None:
        self._lexicons: Mapping[LanguageCode, _Lexicon] = MappingProxyType(dict(lexicons))

    @classmethod
    def load(cls, root: Path, profiles: LanguageProfiles) -> "LexiconFactExtractor":
        lexicons: dict[LanguageCode, _Lexicon] = {}

        for language in profiles.languages:
            profile: LanguageProfile = profiles.get(language)
            document: LexiconFile = read_yaml(root / language / _LEXICON_FILE, LexiconFile)
            negations: frozenset[str] = frozenset(
                profile.normalize(word) for word in document.negations
            )
            lexicons[language] = _Lexicon(
                profile=profile,
                negations=negations,
                negation_window=document.negation_window,
                manifestations=cls._index(document.manifestations, profile, negations),
                stressors=cls._index(document.stressors, profile, negations),
            )

        return cls(lexicons)

    @staticmethod
    def _index(
        terms: Mapping[TermId, Iterable[str]],
        profile: LanguageProfile,
        negations: frozenset[str],
    ) -> _PhraseIndex:
        """Группирует фразы по основе первого слова, длинные фразы — раньше."""
        index: dict[str, list[_Phrase]] = {}

        for term, phrases in terms.items():
            for phrase in phrases:
                tokens: tuple[Token, ...] = profile.tokenize(phrase)
                if not tokens:
                    continue

                entry: _Phrase = _Phrase(
                    term=term,
                    stems=tuple(token.stem for token in tokens),
                    negative=tokens[0].word in negations,
                )
                index.setdefault(entry.stems[0], []).append(entry)

        ordered: _PhraseIndex = MappingProxyType(
            {
                stem: tuple(sorted(entries, key=lambda entry: -len(entry.stems)))
                for stem, entries in index.items()
            },
        )
        return ordered

    @staticmethod
    def _matches(
        tokens: tuple[Token, ...],
        position: int,
        phrase: _Phrase,
        lexicon: _Lexicon,
    ) -> bool:
        """Основы фразы идут подряд и перед ней нет отрицания, если фраза сама не отрицание."""
        window: tuple[Token, ...] = tokens[position : position + len(phrase.stems)]
        if tuple(token.stem for token in window) != phrase.stems:
            return False

        before: tuple[Token, ...] = tokens[max(0, position - lexicon.negation_window) : position]
        negated: bool = any(token.word in lexicon.negations for token in before)
        return phrase.negative or not negated

    @override
    async def extract(self, text: str, language: LanguageCode) -> CaseFacts:
        lexicon: _Lexicon | None = self._lexicons.get(language)
        if lexicon is None:
            raise UnsupportedLanguageError(language=language)

        tokens: tuple[Token, ...] = lexicon.profile.tokenize(text)

        return CaseFacts(
            manifestations=self._find(text, tokens, lexicon, lexicon.manifestations),
            stressors=self._find(text, tokens, lexicon, lexicon.stressors),
        )

    def _find(
        self,
        text: str,
        tokens: tuple[Token, ...],
        lexicon: _Lexicon,
        index: _PhraseIndex,
    ) -> tuple[Evidence, ...]:
        """Находки по порядку в тексте; цитата — совпавший фрагмент реплики."""
        found: list[Evidence] = []

        for position, token in enumerate(tokens):
            for phrase in index.get(token.stem, ()):
                if self._matches(tokens, position, phrase, lexicon):
                    last: Token = tokens[position + len(phrase.stems) - 1]
                    found.append(Evidence(term=phrase.term, quote=text[token.start : last.end]))

        return tuple(found)
