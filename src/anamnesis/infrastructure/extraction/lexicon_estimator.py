from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Final, override

from anamnesis.application.dto.estimate import Estimate, LinguisticTerm
from anamnesis.application.errors.knowledge import UnsupportedLanguageError
from anamnesis.application.interfaces.extraction.estimate_extractor import IEstimateExtractor
from anamnesis.domain.enums.fact_kind import ESTIMATED_FACTS, FactKind
from anamnesis.domain.types import LanguageCode
from anamnesis.infrastructure.filesystem.yaml_reader import read_yaml
from anamnesis.infrastructure.fuzzy.variables import LinguisticVariables
from anamnesis.infrastructure.text.language import LanguageProfile, LanguageProfiles, Token
from anamnesis.infrastructure.text.patterns import PatternFile, PatternMatch, PatternMatcher


_FUZZY_FILE: Final[str] = "fuzzy.yaml"

type _Weights = Mapping[LinguisticTerm, float]
"""Степени термов лингвистической переменной."""

type _Expressions = Mapping[str, LinguisticTerm | _Weights]
"""Выражения сведения и их термы: один терм со степенью 1 или несколько со степенями."""


class FuzzyFile(PatternFile):
    """`resources/<язык>/fuzzy.yaml`: слова, по которым оцениваются длительность, частота, влияние.

    Attributes:
        numbers: Числа словами.
        units: Единицы после числа и их вес в единицах универсума, по сведениям.
        expressions: Размытые выражения и их термы, по сведениям.
    """

    numbers: Mapping[str, float]
    units: Mapping[FactKind, Mapping[str, float]]
    expressions: Mapping[FactKind, _Expressions]


@dataclass(frozen=True, slots=True)
class _Dictionary:
    """Словарь одного языка, готовый к поиску."""

    profile: LanguageProfile
    numbers: Mapping[str, float]
    units: Mapping[FactKind, PatternMatcher[float]]
    expressions: Mapping[FactKind, PatternMatcher[str]]
    weights: Mapping[FactKind, Mapping[str, _Weights]]


class LexiconEstimateExtractor(IEstimateExtractor):
    """Оценивает длительность, частоту и влияние по словарю `fuzzy.yaml`.

    Число с единицей даёт точную оценку; из диапазона «2–3 недели» берётся
    нижняя граница. Без числа размытые выражения дают степени термов,
    несколько выражений объединяются по максимуму.
    """

    def __init__(self, dictionaries: Mapping[LanguageCode, _Dictionary]) -> None:
        self._dictionaries: Mapping[LanguageCode, _Dictionary] = MappingProxyType(
            dict(dictionaries)
        )

    @classmethod
    def load(
        cls,
        root: Path,
        profiles: LanguageProfiles,
        variables: LinguisticVariables,
    ) -> "LexiconEstimateExtractor":
        dictionaries: dict[LanguageCode, _Dictionary] = {}
        for language in profiles.languages:
            document: FuzzyFile = read_yaml(root / language / _FUZZY_FILE, FuzzyFile)
            cls._validate_terms(document, variables)
            dictionaries[language] = cls._dictionary(document, profiles.get(language))
        return cls(dictionaries)

    @staticmethod
    def _dictionary(document: FuzzyFile, profile: LanguageProfile) -> _Dictionary:
        """Словарь языка: числа, поиск единиц и выражений, степени термов выражений."""
        return _Dictionary(
            profile=profile,
            numbers=MappingProxyType(
                {profile.normalize(word): value for word, value in document.numbers.items()},
            ),
            units=MappingProxyType(
                {
                    fact: PatternMatcher(_group_by_value(units), profile=profile)
                    for fact, units in document.units.items()
                },
            ),
            expressions=MappingProxyType(
                {
                    fact: PatternMatcher(
                        {expression: (expression,) for expression in expressions},
                        profile=profile,
                        negations=document.negations,
                        negation_window=document.negation_window,
                    )
                    for fact, expressions in document.expressions.items()
                },
            ),
            weights=MappingProxyType(
                {
                    fact: MappingProxyType(
                        {expression: _weights(terms) for expression, terms in expressions.items()},
                    )
                    for fact, expressions in document.expressions.items()
                },
            ),
        )

    @staticmethod
    def _validate_terms(document: FuzzyFile, variables: LinguisticVariables) -> None:
        """Выражения ссылаются только на термы переменных домена.

        Raises:
            ValueError: Вид сведения не оценивается или терма у переменной нет.
        """
        for fact, expressions in document.expressions.items():
            if fact not in ESTIMATED_FACTS:
                raise ValueError(f"'{fact}' is not an estimated fact")

            known: Mapping[LinguisticTerm, object] = variables[fact].terms
            for expression, terms in expressions.items():
                for term in _weights(terms):
                    if term not in known:
                        raise ValueError(
                            f"Expression '{expression}' refers to unknown term '{term}'"
                        )

    @override
    async def extract(self, text: str, fact: FactKind, language: LanguageCode) -> Estimate | None:
        dictionary: _Dictionary | None = self._dictionaries.get(language)
        if dictionary is None:
            raise UnsupportedLanguageError(language=language)

        tokens: tuple[Token, ...] = dictionary.profile.tokenize(text)

        value: float | None = _exact_value(tokens, dictionary, fact)
        if value is not None:
            return Estimate(fact=fact, value=value)

        weights: _Weights = _expression_weights(tokens, dictionary, fact)
        return Estimate(fact=fact, terms=weights) if weights else None


def _weights(terms: LinguisticTerm | _Weights) -> _Weights:
    """Один терм означает степень 1."""
    if isinstance(terms, str):
        return MappingProxyType({terms: 1.0})
    return terms


def _group_by_value(units: Mapping[str, float]) -> Mapping[float, tuple[str, ...]]:
    """Шаблоны единиц, сгруппированные по весу: вес служит ключом находки."""
    grouped: dict[float, list[str]] = {}

    for unit, value in units.items():
        grouped.setdefault(value, []).append(unit)

    return MappingProxyType({value: tuple(items) for value, items in grouped.items()})


def _exact_value(
    tokens: tuple[Token, ...], dictionary: _Dictionary, fact: FactKind
) -> float | None:
    """Первое число с единицей; у диапазона берётся меньшее число."""
    matcher: PatternMatcher[float] | None = dictionary.units.get(fact)
    if matcher is None:
        return None

    for match in matcher.find(tokens):
        count: float | None = _number_before(tokens, match.first, dictionary.numbers)
        if count is not None:
            return count * match.key

    return None


def _number_before(
    tokens: tuple[Token, ...],
    position: int,
    numbers: Mapping[str, float],
) -> float | None:
    """Число прямо перед словом; диапазон «2–3» даёт меньшее из двух чисел."""
    if position == 0 or tokens[position].clause_break:
        return None

    count: float | None = _number(tokens[position - 1], numbers)
    if count is None:
        return None

    if position > 1:
        previous: float | None = _number(tokens[position - 2], numbers)
        if previous is not None:
            return min(previous, count)

    return count


def _number(token: Token, numbers: Mapping[str, float]) -> float | None:
    """Число из слова: цифрами или словом из словаря."""
    if token.word.isdigit():
        return float(token.word)
    return numbers.get(token.word)


def _expression_weights(
    tokens: tuple[Token, ...],
    dictionary: _Dictionary,
    fact: FactKind,
) -> _Weights:
    """Степени термов по всем внешним находкам, объединённые по максимуму."""
    matcher: PatternMatcher[str] | None = dictionary.expressions.get(fact)
    if matcher is None:
        return MappingProxyType({})

    combined: dict[LinguisticTerm, float] = {}
    for match in _outermost(matcher.find(tokens)):
        for term, degree in dictionary.weights[fact][match.key].items():
            combined[term] = max(combined.get(term, 0.0), degree)

    return MappingProxyType(combined)


def _outermost(matches: tuple[PatternMatch[str], ...]) -> tuple[PatternMatch[str], ...]:
    """Находки, не вложенные в более длинные находки других выражений."""
    outermost: tuple[PatternMatch[str], ...] = tuple(
        match
        for match in matches
        if not any(
            other.first <= match.first
            and match.last <= other.last
            and (other.first, other.last) != (match.first, match.last)
            for other in matches
        )
    )
    return outermost
