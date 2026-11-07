from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import override

from anamnesis.application.dto.estimate import Estimate, LinguisticTerm
from anamnesis.application.interfaces.extraction.estimate_extractor import IEstimateExtractor
from anamnesis.domain.enums.fact_kind import ESTIMATED_FACTS, FactKind
from anamnesis.domain.types import LanguageCode
from anamnesis.infrastructure.fuzzy.linguistic_variable import LinguisticVariable
from anamnesis.infrastructure.localization.locale import Fuzzy, Locale
from anamnesis.infrastructure.text.patterns import PatternMatch, PatternMatcher
from anamnesis.infrastructure.text.tokens import Stemmer, Token, make_stemmer, tokenize


type _Weights = Mapping[LinguisticTerm, float]


@dataclass(frozen=True, slots=True)
class _Index:
    """Словарь одного языка: числа, единицы и выражения по видам сведений."""

    stemmer: Stemmer
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

    def __init__(
        self,
        locales: Mapping[LanguageCode, Locale],
        variables: Mapping[FactKind, LinguisticVariable],
    ) -> None:
        self._indexes: Mapping[LanguageCode, _Index] = MappingProxyType(
            {
                language: _build_index(locale.fuzzy, variables)
                for language, locale in locales.items()
            },
        )

    @override
    async def extract(self, text: str, fact: FactKind, language: LanguageCode) -> Estimate | None:
        index: _Index = self._indexes[language]
        tokens: tuple[Token, ...] = tokenize(text, index.stemmer)
        value: float | None = _exact_value(tokens, index, fact)
        if value is not None:
            return Estimate(fact=fact, value=value)
        weights: _Weights = _expression_weights(tokens, index, fact)
        return Estimate(fact=fact, terms=weights) if weights else None


def _build_index(fuzzy: Fuzzy, variables: Mapping[FactKind, LinguisticVariable]) -> _Index:
    _validate_terms(fuzzy, variables)
    stemmer: Stemmer = make_stemmer(fuzzy.stemmer)
    return _Index(
        stemmer=stemmer,
        numbers=MappingProxyType(
            {_normalize_word(word): value for word, value in fuzzy.numbers.items()},
        ),
        units=MappingProxyType(
            {
                fact: PatternMatcher(
                    _group_by_value(units),
                    stemmer=stemmer,
                    negations=(),
                )
                for fact, units in fuzzy.units.items()
            },
        ),
        expressions=MappingProxyType(
            {
                fact: PatternMatcher(
                    {expression: (expression,) for expression in expressions},
                    stemmer=stemmer,
                    negations=fuzzy.negations,
                )
                for fact, expressions in fuzzy.expressions.items()
            },
        ),
        weights=MappingProxyType(
            {
                fact: MappingProxyType(
                    {expression: _weights(terms) for expression, terms in expressions.items()},
                )
                for fact, expressions in fuzzy.expressions.items()
            },
        ),
    )


def _validate_terms(fuzzy: Fuzzy, variables: Mapping[FactKind, LinguisticVariable]) -> None:
    """Выражения ссылаются только на термы переменных домена.

    Raises:
        ValueError: Вид сведения не оценивается или терма у переменной нет.
    """
    for fact, expressions in fuzzy.expressions.items():
        if fact not in ESTIMATED_FACTS:
            raise ValueError(f"'{fact}' is not an estimated fact")
        known: Mapping[LinguisticTerm, object] = variables[fact].terms
        for expression, terms in expressions.items():
            for term in _weights(terms):
                if term not in known:
                    raise ValueError(f"Expression '{expression}' refers to unknown term '{term}'")


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


def _exact_value(tokens: tuple[Token, ...], index: _Index, fact: FactKind) -> float | None:
    """Первое число с единицей; у диапазона берётся меньшее число."""
    matcher: PatternMatcher[float] | None = index.units.get(fact)
    if matcher is None:
        return None
    for match in matcher.find(tokens):
        count: float | None = _number_before(tokens, match.first, index.numbers)
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
    if token.word.isdigit():
        return float(token.word)
    return numbers.get(token.word)


def _expression_weights(tokens: tuple[Token, ...], index: _Index, fact: FactKind) -> _Weights:
    """Степени термов по всем внешним находкам, объединённые по максимуму."""
    matcher: PatternMatcher[str] | None = index.expressions.get(fact)
    if matcher is None:
        return MappingProxyType({})
    combined: dict[LinguisticTerm, float] = {}
    for match in _outermost(matcher.find(tokens)):
        for term, degree in index.weights[fact][match.key].items():
            combined[term] = max(combined.get(term, 0.0), degree)
    return MappingProxyType(combined)


def _outermost(matches: tuple[PatternMatch[str], ...]) -> tuple[PatternMatch[str], ...]:
    """Находки, не вложенные в более длинные находки других выражений."""
    return tuple(
        match
        for match in matches
        if not any(
            other.first <= match.first
            and match.last <= other.last
            and (other.first, other.last) != (match.first, match.last)
            for other in matches
        )
    )


def _normalize_word(word: str) -> str:
    return word.lower().replace("ё", "е")
