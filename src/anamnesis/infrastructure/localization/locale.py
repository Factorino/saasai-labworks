from collections.abc import Mapping
from pathlib import Path
from types import MappingProxyType
from typing import Any, ClassVar, Final

from pydantic import BaseModel, ConfigDict, Field
import yaml

from anamnesis.domain.enums.chat_stage import ChatStage
from anamnesis.domain.enums.crisis_category import CrisisCategory
from anamnesis.domain.enums.fact_kind import FactKind
from anamnesis.domain.enums.referral import Referral
from anamnesis.domain.enums.violation_kind import ViolationKind
from anamnesis.domain.types import LanguageCode, OptionCode, RuleId, TermId


class _File(BaseModel):
    """Схема YAML-файла локали; лишние ключи — ошибка."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="forbid")


class QuestionTexts(_File):
    """Формулировки вопроса и подписи его вариантов."""

    text: str
    follow_up: str | None = None
    options: Mapping[OptionCode, str] = Field(default_factory=dict)


class Helpline(_File):
    """Служба помощи: название, телефон и пояснение."""

    name: str
    phone: str
    note: str = ""


class Messages(_File):
    """`messages.yaml`: тексты интерфейса по кодам домена."""

    greeting: str
    crisis_message: str
    support_others: str
    helplines: tuple[Helpline, ...]
    disclaimer: str
    replies: Mapping[ChatStage, str]
    levels: Mapping[str, str]
    specialists: Mapping[str, str]
    refuse: str
    referrals: Mapping[Referral, str]
    questions: Mapping[FactKind, QuestionTexts]
    rules: Mapping[RuleId, str]


class Terms(_File):
    """`terms.yaml`: названия и описания понятий онтологии."""

    names: Mapping[TermId, str]
    descriptions: Mapping[TermId, str]
    sources: Mapping[TermId, str] = Field(default_factory=dict)


class Lexicon(_File):
    """`lexicon.yaml`: фразы, по которым находятся термины онтологии."""

    stemmer: str
    manifestations: Mapping[TermId, tuple[str, ...]]
    stressors: Mapping[TermId, tuple[str, ...]]


class Crisis(_File):
    """`crisis.yaml`: шаблоны кризисного детектора.

    Шаблон — слова через пробел, `...` — пропуск до нескольких слов.
    """

    stemmer: str
    negations: tuple[str, ...]
    first_person: tuple[str, ...]
    others: tuple[str, ...]
    patterns: Mapping[CrisisCategory, tuple[str, ...]]


class Guard(_File):
    """`guard.yaml`: шаблоны проверки ответов системы.

    `codes` — регулярные выражения кодов МКБ; `levels` — утверждения об уровне
    срочности (`L0`–`L3`), по которым видно расхождение с правилами.
    """

    stemmer: str
    negations: tuple[str, ...]
    patterns: Mapping[ViolationKind, tuple[str, ...]]
    codes: tuple[str, ...]
    levels: Mapping[str, tuple[str, ...]]


class Locale(_File):
    """Все тексты одного языка."""

    language: LanguageCode
    messages: Messages
    terms: Terms
    lexicon: Lexicon
    crisis: Crisis
    guard: Guard


_FILES: Final[Mapping[str, str]] = MappingProxyType(
    {
        "messages": "messages.yaml",
        "terms": "terms.yaml",
        "lexicon": "lexicon.yaml",
        "crisis": "crisis.yaml",
        "guard": "guard.yaml",
    },
)
"""Файлы, без которых язык не поддерживается."""


def load_locales(root: Path) -> Mapping[LanguageCode, Locale]:
    """Загружает языки из подкаталогов `root`, в которых есть все файлы локали."""
    locales: dict[LanguageCode, Locale] = {}
    for directory in sorted(path for path in root.iterdir() if path.is_dir()):
        if not all((directory / name).is_file() for name in _FILES.values()):
            continue
        language: LanguageCode = LanguageCode(directory.name)
        data: dict[str, Any] = {key: _read(directory / name) for key, name in _FILES.items()}
        locales[language] = Locale.model_validate({"language": language, **data})
    return MappingProxyType(locales)


def _read(path: Path) -> Any:
    with path.open(encoding="utf-8") as file:
        return yaml.safe_load(file)
