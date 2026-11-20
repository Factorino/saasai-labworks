from typing import TYPE_CHECKING

from dishka import AsyncContainer
import pytest

from anamnesis.application.interfaces.knowledge.knowledge_base import IKnowledgeBase
from anamnesis.application.queries.assessment.assess_case import AssessCaseRequest
from anamnesis.application.services.rendering import ViewRenderer
from anamnesis.domain.enums.recommendation import Referral, UrgencyLevel
from anamnesis.domain.services.practice_selection import PracticeSelection
from anamnesis.domain.types import TermId
from anamnesis.domain.value_objects.assessment import Assessment
from anamnesis.domain.value_objects.case_facts import CaseFacts
from anamnesis.domain.value_objects.practice import PracticeAdvice
from anamnesis.infrastructure.filesystem.yaml_reader import YamlFile
from anamnesis.infrastructure.reasoning.ontology import open_ontology
from anamnesis.main.config.knowledge import KnowledgeConfig
from tests.integration.support.cases import LevelName, read_cases
from tests.integration.support.service import RU, Service


if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

    from anamnesis.application.dto.views.summary import PracticeView, SummaryView
    from anamnesis.application.interfaces.knowledge.knowledge_base import PracticeGuide


class Advice(YamlFile):
    practice: TermId
    cautions: frozenset[TermId] = frozenset()
    clusters: frozenset[TermId] = frozenset()


class Case(YamlFile):
    name: str
    level: LevelName | None
    clusters: tuple[TermId, ...]
    practices: tuple[Advice, ...]
    expected: tuple[TermId, ...]


class Cases(YamlFile):
    cases: tuple[Case, ...]


@pytest.mark.parametrize(
    "case",
    [pytest.param(case, id=case.name) for case in read_cases("selection_cases", Cases).cases],
)
async def test_selection(case: Case, container: AsyncContainer) -> None:
    selection: PracticeSelection = await container.get(PracticeSelection)
    selected: tuple[PracticeAdvice, ...] = selection.select(
        (
            PracticeAdvice(practice=item.practice, cautions=item.cautions, clusters=item.clusters)
            for item in case.practices
        ),
        level=case.level,
        clusters=case.clusters,
    )
    assert tuple(item.practice for item in selected) == case.expected


async def test_documented_practices_match_the_ontology(container: AsyncContainer) -> None:
    config: KnowledgeConfig = await container.get(KnowledgeConfig)
    knowledge: IKnowledgeBase = await container.get(IKnowledgeBase)
    with open_ontology(config.ontology_path) as ontology:
        recommended: set[str] = {p.name for _, p in ontology.recommendsPractice.get_relations()}
    files: Iterator[Path] = (config.locales_dir / RU / "practices").glob("*.yaml")
    documented: set[TermId] = {TermId(f"{file.stem}_") for file in files}
    assert documented <= recommended
    assert recommended - documented <= {"AssertiveCommunication_", "ValuesBasedAction_"}
    for term in documented:
        guide: PracticeGuide | None = knowledge.practice_guide(RU, term)
        assert guide is not None
        assert guide.steps
        assert guide.sources
        assert all(source.url.startswith("https://") for source in guide.sources)


async def test_summary_includes_the_document_and_cautions_for_recommended_practices(
    container: AsyncContainer,
) -> None:
    renderer: ViewRenderer = await container.get(ViewRenderer)
    assessment: Assessment = Assessment(
        level=UrgencyLevel.L1,
        practices=(
            PracticeAdvice(
                practice=TermId("BreathingPractice_"),
                cautions=frozenset({TermId("BreathingDifficulty_")}),
            ),
            PracticeAdvice(practice=TermId("ValuesBasedAction_")),
        ),
    )
    summary: SummaryView = renderer.summary(RU, assessment, CaseFacts())
    practice: PracticeView
    (practice,) = summary.practices
    assert practice.term == "BreathingPractice_"
    knowledge: IKnowledgeBase = await container.get(IKnowledgeBase)
    guide: PracticeGuide | None = knowledge.practice_guide(RU, practice.term)
    assert guide is not None
    assert practice.guide.limits == guide.limits
    assert practice.guide.limits
    assert [caution.term for caution in practice.cautions] == ["BreathingDifficulty_"]
    assert practice.cautions[0].name


@pytest.mark.parametrize(
    ("manifestation", "referral", "show_contacts"),
    [
        ("face_droops", Referral.EMERGENCY_MEDICAL_CARE, True),
        ("want_to_hurt_myself", Referral.CRISIS_HELPLINE, True),
        ("tinnitus_complaint", Referral.DOCTOR_VISIT, False),
        ("feel_anxious", None, False),
    ],
)
async def test_contacts_follow_the_referral(
    manifestation: str, referral: Referral | None, show_contacts: bool, service: Service
) -> None:
    summary: SummaryView = await service.assess(
        AssessCaseRequest(language=RU, manifestations=(TermId(manifestation),))
    )
    assert {item.referral for item in summary.referrals} == ({referral} if referral else set())
    assert bool(summary.helplines) is show_contacts
    assert all(contact.phone for contact in summary.helplines)
