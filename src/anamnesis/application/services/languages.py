from collections.abc import Iterable

from anamnesis.application.errors.knowledge import UnsupportedLanguageError
from anamnesis.domain.types import LanguageCode


class SupportedLanguages:
    """Языки, на которых можно вести диалог."""

    def __init__(self, languages: Iterable[LanguageCode]) -> None:
        self._languages: frozenset[LanguageCode] = frozenset(languages)

    def validate(self, language: LanguageCode) -> None:
        if language not in self._languages:
            raise UnsupportedLanguageError(language=language)
