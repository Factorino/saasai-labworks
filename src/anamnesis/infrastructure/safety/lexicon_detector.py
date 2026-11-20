from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Final, override

from anamnesis.application.errors.knowledge import UnsupportedLanguageError
from anamnesis.application.interfaces.safety.crisis_detector import ICrisisDetector
from anamnesis.domain.enums.crisis import CrisisCategory
from anamnesis.domain.types import LanguageCode
from anamnesis.domain.value_objects.crisis_signal import CrisisSignal
from anamnesis.infrastructure.filesystem.yaml_reader import read_yaml
from anamnesis.infrastructure.text.language import LanguageProfile, LanguageProfiles, Token
from anamnesis.infrastructure.text.patterns import PatternFile, PatternMatch, PatternMatcher


_CRISIS_FILE: Final[str] = "crisis.yaml"


class CrisisFile(PatternFile):
    """`resources/<язык>/crisis.yaml`: шаблоны кризисного детектора.

    Attributes:
        first_person: Слова о самом пользователе: «я», «мне».
        others: Слова о другом человеке: «подруга», «он»; сравниваются по основам.
        not_others: Слова с основой из `others`, которые не о людях: «другой».
        patterns: Шаблоны по категориям находок.
    """

    first_person: tuple[str, ...]
    others: tuple[str, ...]
    not_others: tuple[str, ...]
    patterns: Mapping[CrisisCategory, tuple[str, ...]]


@dataclass(frozen=True, slots=True)
class _Patterns:
    """Шаблоны одного языка и слова, по которым видно, о ком речь."""

    profile: LanguageProfile
    matcher: PatternMatcher[CrisisCategory]
    first_person: frozenset[str]
    others: frozenset[str]
    not_others: frozenset[str]


class LexiconCrisisDetector(ICrisisDetector):
    """Находит кризисные формулировки по шаблонам `crisis.yaml`.

    Если ближайшее действующее лицо перед находкой — другой человек
    («подруга сказала, что хочет умереть»), находка становится тревогой за
    другого. В сомнительных случаях находка остаётся кризисной: пропуск хуже
    ложного срабатывания.
    """

    def __init__(self, patterns: Mapping[LanguageCode, _Patterns]) -> None:
        self._patterns: Mapping[LanguageCode, _Patterns] = MappingProxyType(dict(patterns))

    @classmethod
    def load(cls, root: Path, profiles: LanguageProfiles) -> "LexiconCrisisDetector":
        patterns: dict[LanguageCode, _Patterns] = {}

        for language in profiles.languages:
            profile: LanguageProfile = profiles.get(language)
            document: CrisisFile = read_yaml(root / language / _CRISIS_FILE, CrisisFile)
            patterns[language] = _Patterns(
                profile=profile,
                matcher=PatternMatcher(
                    document.patterns,
                    profile=profile,
                    negations=document.negations,
                    negation_window=document.negation_window,
                ),
                first_person=frozenset(profile.normalize(word) for word in document.first_person),
                others=frozenset(profile.stem(word) for word in document.others),
                not_others=frozenset(profile.normalize(word) for word in document.not_others),
            )

        return cls(patterns)

    @staticmethod
    def _about_other(
        tokens: tuple[Token, ...],
        match: PatternMatch[CrisisCategory],
        patterns: _Patterns,
    ) -> bool:
        """Ближайшее действующее лицо перед находкой в том же предложении — другой человек."""
        position: int = match.first

        while position > 0 and not tokens[position].sentence_break:
            position -= 1
            token: Token = tokens[position]
            if token.word in patterns.first_person:
                return False
            if token.stem in patterns.others and token.word not in patterns.not_others:
                return True

        return False

    @override
    async def detect(self, text: str, language: LanguageCode) -> tuple[CrisisSignal, ...]:
        patterns: _Patterns | None = self._patterns.get(language)
        if patterns is None:
            raise UnsupportedLanguageError(language=language)

        tokens: tuple[Token, ...] = patterns.profile.tokenize(text)

        signals: dict[CrisisSignal, None] = {}
        for match in patterns.matcher.find(tokens):
            category: CrisisCategory = (
                CrisisCategory.OTHER_PERSON
                if self._about_other(tokens, match, patterns)
                else match.key
            )
            quote: str = text[tokens[match.first].start : tokens[match.last].end]
            signals.setdefault(CrisisSignal(category=category, quote=quote))

        return tuple(signals)
