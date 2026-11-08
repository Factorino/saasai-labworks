"""База практик: документы сходятся с онтологией, в сводке только практики с документом."""

from typing import Any

from owlready2 import World

from anamnesis.application.services.rendering import ViewRenderer
from anamnesis.domain.enums.urgency_level import UrgencyLevel
from anamnesis.domain.types import TermId
from anamnesis.domain.value_objects.assessment import Assessment
from anamnesis.domain.value_objects.case_facts import CaseFacts
from anamnesis.domain.value_objects.inference import PracticeAdvice
from tests.integration.harness import CATALOG, LOCALES, ROOT, RU


NOT_DOCUMENTED = {"AssertiveCommunication_", "ValuesBasedAction_"}
"""Рекомендуются онтологией, но источник не удалось прочитать, поэтому не советуются."""
DOCUMENTS = LOCALES[RU].practices


def recommended_practices() -> set[str]:
    world: Any = World()
    try:
        onto: Any = world.get_ontology((ROOT / "ontology" / "anamnesis.owl").as_uri()).load()
        return {practice.name for _, practice in onto.recommendsPractice.get_relations()}
    finally:
        world.close()


def test_every_recommended_practice_has_a_document() -> None:
    assert recommended_practices() - set(DOCUMENTS) == NOT_DOCUMENTED


def test_every_document_is_a_recommended_practice() -> None:
    assert set(DOCUMENTS) <= recommended_practices()


def test_every_file_is_a_separate_document() -> None:
    files = list((ROOT / "locales" / "ru" / "practices").glob("*.yaml"))

    assert len(DOCUMENTS) == len(files)
    assert len(DOCUMENTS) >= 20


def test_documents_cite_open_sources() -> None:
    for document in DOCUMENTS.values():
        assert all(source.url.startswith("https://") for source in document.sources)


def test_summary_shows_only_documented_practices() -> None:
    assessment = Assessment(
        level=UrgencyLevel.L1,
        practices=(
            PracticeAdvice(practice=TermId("WorryTime_")),
            PracticeAdvice(practice=TermId("ValuesBasedAction_")),
        ),
    )

    summary = ViewRenderer(CATALOG).summary(assessment, CaseFacts(), RU)

    assert [practice.term for practice in summary.practices] == ["WorryTime_"]
    assert summary.practices[0].guide.steps
    assert summary.practices[0].guide.sources
