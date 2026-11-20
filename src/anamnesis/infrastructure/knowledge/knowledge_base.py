from collections.abc import Iterable, Mapping
from pathlib import Path
from types import MappingProxyType
from typing import Final, override

from pydantic import Field

from anamnesis.application.errors.knowledge import UnsupportedLanguageError
from anamnesis.application.interfaces.knowledge.knowledge_base import (
    Helpline,
    IKnowledgeBase,
    PracticeGuide,
    PracticeSource,
)
from anamnesis.domain.types import LanguageCode, TermId
from anamnesis.infrastructure.filesystem.yaml_reader import YamlFile, read_yaml


_HELPLINES_FILE: Final[str] = "helplines.yaml"
_PRACTICES_DIRECTORY: Final[str] = "practices"

type _Helplines = tuple[Helpline, ...]
type _PracticeGuides = Mapping[TermId, PracticeGuide]


class HelplineEntry(YamlFile):
    """Служба помощи.

    Attributes:
        name: Название службы.
        phone: Номер телефона.
        note: Пояснение: часы работы, для кого служба.
    """

    name: str
    phone: str
    note: str = ""


class HelplinesFile(YamlFile):
    """`helplines.yaml`: службы помощи для региона языка."""

    helplines: tuple[HelplineEntry, ...] = Field(min_length=1)


class PracticeSourceEntry(YamlFile):
    """Открытый источник, который пересказывает документ практики.

    Attributes:
        title: Название источника.
        url: Ссылка.
    """

    title: str
    url: str


class PracticeFile(YamlFile):
    """`practices/*.yaml`: как выполнять практику, её ограничения и источники.

    Attributes:
        term: Представитель практики в онтологии.
        steps: Шаги выполнения.
        limits: Ограничения.
        sources: Источники.
    """

    term: TermId
    steps: tuple[str, ...] = Field(min_length=1)
    limits: tuple[str, ...] = ()
    sources: tuple[PracticeSourceEntry, ...] = Field(min_length=1)


class YamlKnowledgeBase(IKnowledgeBase):
    """Справочные материалы из `locales/<язык>/`: службы помощи и документы практик."""

    def __init__(
        self,
        *,
        helplines: Mapping[LanguageCode, _Helplines],
        practices: Mapping[LanguageCode, _PracticeGuides],
    ) -> None:
        self._helplines: Mapping[LanguageCode, _Helplines] = MappingProxyType(dict(helplines))
        self._practices: Mapping[LanguageCode, _PracticeGuides] = MappingProxyType(dict(practices))

    @classmethod
    def load(cls, root: Path, languages: Iterable[LanguageCode]) -> "YamlKnowledgeBase":
        helplines: dict[LanguageCode, _Helplines] = {}
        practices: dict[LanguageCode, _PracticeGuides] = {}

        for language in languages:
            directory: Path = root / language
            helplines[language] = cls._read_helplines(directory / _HELPLINES_FILE)
            practices[language] = cls._read_practices(directory / _PRACTICES_DIRECTORY)

        knowledge: YamlKnowledgeBase = cls(helplines=helplines, practices=practices)
        return knowledge

    @staticmethod
    def _read_helplines(path: Path) -> _Helplines:
        document: HelplinesFile = read_yaml(path, HelplinesFile)
        helplines: _Helplines = tuple(
            Helpline(name=entry.name, phone=entry.phone, note=entry.note)
            for entry in document.helplines
        )
        return helplines

    @staticmethod
    def _read_practices(directory: Path) -> _PracticeGuides:
        guides: dict[TermId, PracticeGuide] = {}
        if not directory.is_dir():
            return MappingProxyType(guides)

        for path in sorted(directory.glob("*.yaml")):
            document: PracticeFile = read_yaml(path, PracticeFile)
            if document.term in guides:
                raise ValueError(f"Practice '{document.term}' is described twice: {path}")

            guides[document.term] = PracticeGuide(
                steps=document.steps,
                limits=document.limits,
                sources=tuple(
                    PracticeSource(title=source.title, url=source.url)
                    for source in document.sources
                ),
            )

        return MappingProxyType(guides)

    @override
    def helplines(self, language: LanguageCode) -> tuple[Helpline, ...]:
        helplines: _Helplines | None = self._helplines.get(language)
        if helplines is None:
            raise UnsupportedLanguageError(language=language)
        return helplines

    @override
    def practice_guide(self, language: LanguageCode, practice: TermId) -> PracticeGuide | None:
        guides: _PracticeGuides | None = self._practices.get(language)
        if guides is None:
            raise UnsupportedLanguageError(language=language)
        return guides.get(practice)
