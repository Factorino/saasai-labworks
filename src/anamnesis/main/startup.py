from collections.abc import Iterable, Set as AbstractSet

from dishka import AsyncContainer

from anamnesis.domain.types import LanguageCode
from anamnesis.infrastructure.localization.catalog import TextCatalog, TextCatalogs
from anamnesis.infrastructure.reasoning.ontology import OntologyNames
from anamnesis.main.config.knowledge import KnowledgeConfig
from anamnesis.main.di.providers.interactors import INTERACTORS


async def prepare(container: AsyncContainer) -> None:
    """Загружает все данные до первого запроса и сверяет их между собой."""
    async with container() as request_container:
        for interactor in INTERACTORS:
            await request_container.get(interactor)

    config: KnowledgeConfig = await container.get(KnowledgeConfig)
    _check_texts(
        await container.get(TextCatalogs),
        await container.get(OntologyNames),
        config.languages,
    )


def _check_texts(
    catalogs: TextCatalogs,
    names: OntologyNames,
    languages: Iterable[LanguageCode],
) -> None:
    """Объяснение у каждого правила и название у каждого понятия онтологии, лишних нет."""
    problems: list[str] = []

    for language in languages:
        catalog: TextCatalog = catalogs.get(language)
        problems += _differences(f"{language}: rules", names.rules, catalog.messages.rules.keys())
        problems += _differences(f"{language}: terms", names.terms, catalog.terms.names.keys())

    if problems:
        raise ValueError(f"Texts do not match the ontology: {problems}")


def _differences(section: str, expected: AbstractSet[str], present: AbstractSet[str]) -> list[str]:
    """Недостающие и лишние ключи секции."""
    differences: list[str] = [
        *(f"{section} missing {key}" for key in sorted(expected - present)),
        *(f"{section} unknown {key}" for key in sorted(present - expected)),
    ]
    return differences
