"""База практик: документы сходятся с онтологией, подбор по `data/selection_cases.yaml`."""

import asyncio
from pathlib import Path
from typing import Any

from owlready2 import World
import pytest
import yaml

from anamnesis.application.services.rendering import ViewRenderer
from anamnesis.domain.enums.urgency_level import UrgencyLevel
from anamnesis.domain.types import TermId
from anamnesis.domain.value_objects.assessment import Assessment
from anamnesis.domain.value_objects.case_facts import CaseFacts
from anamnesis.domain.value_objects.evidence import Evidence
from anamnesis.domain.value_objects.inference import PracticeAdvice
from anamnesis.infrastructure.reasoning.owl_reasoner import OwlCaseReasoner
from tests.integration.harness import CATALOG, LOCALES, ROOT, RU, SELECTION


NOT_DOCUMENTED = {"AssertiveCommunication_", "ValuesBasedAction_"}
"""Рекомендуются онтологией, но источник не удалось прочитать, поэтому не советуются."""
DOCUMENTS = LOCALES[RU].practices
CASES: list[dict[str, Any]] = yaml.safe_load(
    (Path(__file__).parent / "data" / "selection_cases.yaml").read_text(encoding="utf-8"),
)


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

    summary = ViewRenderer(CATALOG, SELECTION).summary(assessment, CaseFacts(), RU)

    assert [practice.term for practice in summary.practices] == ["WorryTime_"]
    assert summary.practices[0].guide.steps
    assert summary.practices[0].guide.sources


def advice(item: dict[str, Any]) -> PracticeAdvice:
    return PracticeAdvice(
        practice=TermId(item["practice"]),
        cautions=frozenset(TermId(term) for term in item.get("cautions", ())),
        clusters=frozenset(TermId(term) for term in item.get("clusters", ())),
    )


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["name"])
def test_selection(case: dict[str, Any]) -> None:
    level = UrgencyLevel[case["level"]] if case["level"] is not None else None

    selected = SELECTION.select(
        [advice(item) for item in case["practices"]],
        level=level,
        clusters=[TermId(term) for term in case["clusters"]],
    )

    assert [item.practice for item in selected] == case["expected"]


def test_reasoner_reports_clusters_of_a_practice() -> None:
    reasoner = OwlCaseReasoner(ontology_path=ROOT / "ontology" / "anamnesis.owl")
    facts = CaseFacts(manifestations=(Evidence(term=TermId("Anxiety_"), quote=""),))

    result = asyncio.run(reasoner.infer(facts))

    assert any(TermId("AnxietyCluster_") in item.clusters for item in result.practices)
