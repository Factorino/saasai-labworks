from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import override

from anamnesis.application.interfaces.safety.crisis_detector import ICrisisDetector
from anamnesis.domain.enums.crisis_category import CrisisCategory
from anamnesis.domain.types import LanguageCode
from anamnesis.domain.value_objects.crisis_signal import CrisisSignal
from anamnesis.infrastructure.localization.locale import Crisis, Locale
from anamnesis.infrastructure.text.patterns import PatternMatch, PatternMatcher
from anamnesis.infrastructure.text.tokens import Token, make_stemmer, tokenize


@dataclass(frozen=True, slots=True)
class _Index:
    """Шаблоны одного языка и слова, по которым видно, о ком речь."""

    matcher: PatternMatcher[CrisisCategory]
    first_person: frozenset[str]
    others: frozenset[str]


class LexiconCrisisDetector(ICrisisDetector):
    """Находит кризисные формулировки по шаблонам `crisis.yaml`.

    Если ближайшее действующее лицо перед находкой — другой человек
    («подруга сказала, что хочет умереть»), находка становится тревогой за
    другого. В сомнительных случаях находка остаётся кризисной: пропуск хуже
    ложного срабатывания.
    """

    def __init__(self, locales: Mapping[LanguageCode, Locale]) -> None:
        self._indexes: Mapping[LanguageCode, _Index] = MappingProxyType(
            {language: _build_index(locale.crisis) for language, locale in locales.items()},
        )

    @override
    async def detect(self, text: str, language: LanguageCode) -> tuple[CrisisSignal, ...]:
        index: _Index = self._indexes[language]
        tokens: tuple[Token, ...] = tokenize(text, index.matcher.stemmer)
        signals: dict[CrisisSignal, None] = {}
        for match in index.matcher.find(tokens):
            category: CrisisCategory = (
                CrisisCategory.OTHER_PERSON if _about_other(tokens, match, index) else match.key
            )
            quote: str = text[tokens[match.first].start : tokens[match.last].end]
            signals.setdefault(CrisisSignal(category=category, quote=quote))
        return tuple(signals)


def _build_index(crisis: Crisis) -> _Index:
    matcher: PatternMatcher[CrisisCategory] = PatternMatcher(
        crisis.patterns,
        stemmer=make_stemmer(crisis.stemmer),
        negations=crisis.negations,
    )
    return _Index(
        matcher=matcher,
        first_person=frozenset(crisis.first_person),
        others=frozenset(matcher.stemmer.stemWord(word) for word in crisis.others),
    )


def _about_other(
    tokens: tuple[Token, ...],
    match: PatternMatch[CrisisCategory],
    index: _Index,
) -> bool:
    """Ближайшее действующее лицо перед находкой в предложении — другой человек."""
    position: int = match.first
    while position > 0 and not tokens[position].sentence_break:
        position -= 1
        token: Token = tokens[position]
        if token.word in index.first_person:
            return False
        if token.stem in index.others:
            return True
    return False
