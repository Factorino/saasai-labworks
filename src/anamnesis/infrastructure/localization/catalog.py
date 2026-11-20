from collections.abc import Iterable, Mapping, Set as AbstractSet
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Final

from pydantic import Field

from anamnesis.application.errors.knowledge import UnsupportedLanguageError
from anamnesis.domain.enums.chat import ChatStage
from anamnesis.domain.enums.fact_kind import ESTIMATED_FACTS, FactKind
from anamnesis.domain.enums.recommendation import Referral, UrgencyLevel
from anamnesis.domain.services.questionnaire import Questionnaire
from anamnesis.domain.types import LanguageCode, OptionCode, RuleId, TermId
from anamnesis.domain.value_objects.clarification import REFUSE_OPTION_CODE
from anamnesis.infrastructure.filesystem.yaml_reader import YamlFile, read_yaml


INSUFFICIENT_DATA_KEY: Final[str] = "insufficient_data"
"""Ключ текстов уровня, когда уровень не определён."""

_LEVEL_KEYS: Final[frozenset[str]] = frozenset(
    {*(level.name for level in UrgencyLevel), INSUFFICIENT_DATA_KEY},
)
"""Ключи текстов уровня: `L0`–`L3` и «недостаточно данных»."""

_REPLY_STAGES: Final[frozenset[ChatStage]] = frozenset({ChatStage.SUMMARY, ChatStage.CRISIS})
"""Этапы, на которых свободная реплика получает шаблонный ответ."""

_MESSAGES_FILE: Final[str] = "messages.yaml"
_TERMS_FILE: Final[str] = "terms.yaml"

type _RequiredTexts = tuple[str, AbstractSet[str], AbstractSet[str]]
"""Секция `messages.yaml`, ключи, которые в ней нужны, и ключи, которые в ней есть."""


class QuestionTexts(YamlFile):
    """Формулировки вопроса и подписи его вариантов.

    Attributes:
        text: Формулировка вопроса.
        follow_up: Формулировка повторного вопроса; `None` — та же, что основная.
        options: Подписи вариантов по кодам; у отказа — своя, если отличается от общей.
    """

    text: str
    follow_up: str | None = None
    options: Mapping[OptionCode, str] = Field(default_factory=dict)


class Fallback(YamlFile):
    """Безопасные тексты сводки, когда текста модели нет.

    Attributes:
        description: Вместо описания состояния.
        request: Вместо запроса к специалисту.
    """

    description: str
    request: str


class MessagesFile(YamlFile):
    """`messages.yaml`: тексты интерфейса по кодам домена."""

    greeting: str
    crisis_message: str
    support_others: str
    disclaimer: str
    fallback: Fallback
    approximate: Mapping[FactKind, str]
    replies: Mapping[ChatStage, str]
    levels: Mapping[str, str]
    specialists: Mapping[str, str]
    refuse: str
    referrals: Mapping[Referral, str]
    questions: Mapping[FactKind, QuestionTexts]
    rules: Mapping[RuleId, str]


class TermsFile(YamlFile):
    """`terms.yaml`: названия и описания понятий онтологии."""

    names: Mapping[TermId, str]
    descriptions: Mapping[TermId, str]


@dataclass(frozen=True, slots=True)
class TextCatalog:
    """Тексты одного языка.

    Attributes:
        messages: Тексты интерфейса.
        terms: Названия и описания понятий.
    """

    messages: MessagesFile
    terms: TermsFile


class TextCatalogs:
    """Тексты по языкам, загруженные и проверенные при запуске."""

    def __init__(self, catalogs: Mapping[LanguageCode, TextCatalog]) -> None:
        self._catalogs: Mapping[LanguageCode, TextCatalog] = MappingProxyType(dict(catalogs))

    @classmethod
    def load(
        cls,
        root: Path,
        languages: Iterable[LanguageCode],
        questionnaire: Questionnaire,
    ) -> "TextCatalogs":
        catalogs: dict[LanguageCode, TextCatalog] = {}

        for language in languages:
            directory: Path = root / language
            catalog: TextCatalog = TextCatalog(
                messages=read_yaml(directory / _MESSAGES_FILE, MessagesFile),
                terms=read_yaml(directory / _TERMS_FILE, TermsFile),
            )
            cls._validate_completeness(language, catalog.messages, questionnaire)
            catalogs[language] = catalog

        loaded: TextCatalogs = cls(catalogs)
        return loaded

    @classmethod
    def _validate_completeness(
        cls,
        language: LanguageCode,
        messages: MessagesFile,
        questionnaire: Questionnaire,
    ) -> None:
        """Проверяет, что у каждого кода домена и варианта опросника есть текст."""
        missing: list[str] = [
            *cls._missing_codes(messages),
            *cls._missing_questions(messages, questionnaire),
        ]
        if missing:
            raise ValueError(f"Texts for language '{language}' are incomplete: {sorted(missing)}")

    @staticmethod
    def _missing_codes(messages: MessagesFile) -> list[str]:
        """Тексты для кодов домена, которых нет: `<секция>.<ключ>`."""
        sections: tuple[_RequiredTexts, ...] = (
            ("approximate", ESTIMATED_FACTS, messages.approximate.keys()),
            ("replies", _REPLY_STAGES, messages.replies.keys()),
            ("levels", _LEVEL_KEYS, messages.levels.keys()),
            ("specialists", _LEVEL_KEYS, messages.specialists.keys()),
            ("referrals", frozenset(Referral), messages.referrals.keys()),
        )

        missing: list[str] = [
            f"{section}.{key}"
            for section, required, present in sections
            for key in required - present
        ]
        return missing

    @staticmethod
    def _missing_questions(messages: MessagesFile, questionnaire: Questionnaire) -> list[str]:
        """Тексты вопросов опросника и подписи вариантов, кроме отказа, которых нет."""
        missing: list[str] = []

        for kind in questionnaire.ORDER:
            texts: QuestionTexts | None = messages.questions.get(kind)
            if texts is None:
                missing.append(f"questions.{kind}")
                continue

            options: set[OptionCode] = set(questionnaire.question(kind).options)
            missing += [
                f"questions.{kind}.options.{code}"
                for code in options - {REFUSE_OPTION_CODE} - texts.options.keys()
            ]

        return missing

    def get(self, language: LanguageCode) -> TextCatalog:
        catalog: TextCatalog | None = self._catalogs.get(language)
        if catalog is None:
            raise UnsupportedLanguageError(language=language)
        return catalog


def level_key(level: UrgencyLevel | None) -> str:
    """Ключ текстов уровня: `L0`–`L3` или «недостаточно данных»."""
    return level.name if level is not None else INSUFFICIENT_DATA_KEY
