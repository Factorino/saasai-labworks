from typing import TYPE_CHECKING, Final

from dishka import AsyncContainer
from pydantic import Field
import pytest

from anamnesis.application.interfaces.extraction.fact_extractor import IFactExtractor
from anamnesis.application.services.extraction import FactExtraction
from anamnesis.domain.enums.fact_kind import FactKind
from anamnesis.infrastructure.filesystem.yaml_reader import YamlFile
from tests.integration.support.cases import FrequencyName, ImpactName, UserMessage, read_cases
from tests.integration.support.model import ScriptedModel
from tests.integration.support.service import RU, Service


if TYPE_CHECKING:
    from anamnesis.application.dto.views.summary import SummaryView
    from anamnesis.domain.value_objects.case_facts import CaseFacts


class EstimateCase[T](YamlFile):
    text: str
    value: T | None
    confidence: float | None


class Cases(YamlFile):
    duration: tuple[EstimateCase[int], ...]
    frequency: tuple[EstimateCase[FrequencyName], ...]
    impact: tuple[EstimateCase[ImpactName], ...]


CASES: Final[Cases] = read_cases("fuzzy_cases", Cases)


@pytest.mark.parametrize(
    ("fact", "case"),
    [
        pytest.param(fact, case, id=f"{fact}-{case.text}")
        for fact, cases in (
            (FactKind.DURATION, CASES.duration),
            (FactKind.FREQUENCY, CASES.frequency),
            (FactKind.IMPACT, CASES.impact),
        )
        for case in cases
    ],
)
async def test_normalization(
    fact: FactKind, case: EstimateCase[int], container: AsyncContainer, model: ScriptedModel
) -> None:
    extraction: FactExtraction = await container.get(FactExtraction)
    facts: CaseFacts = await extraction.extract(RU, case.text, fact)
    values: dict[FactKind, int | None] = {
        FactKind.DURATION: facts.duration.weeks if facts.duration is not None else None,
        FactKind.FREQUENCY: facts.frequency,
        FactKind.IMPACT: facts.impact,
    }
    assert values[fact] == case.value
    if case.value is not None:
        assert not model.requests
    if case.confidence is None:
        assert fact not in facts.confidence
    else:
        assert facts.confidence[fact] == pytest.approx(case.confidence, abs=0.01)


class LexiconCase(YamlFile):
    text: str
    manifestations: dict[str, str] = Field(default_factory=dict)
    stressors: dict[str, str] = Field(default_factory=dict)


class LexiconCases(YamlFile):
    cases: tuple[LexiconCase, ...]


@pytest.mark.parametrize(
    "case",
    [pytest.param(case, id=case.text) for case in read_cases("lexicon_cases", LexiconCases).cases],
)
async def test_utterance_maps_to_terms_and_evidence(
    case: LexiconCase, container: AsyncContainer
) -> None:
    lexicon: IFactExtractor = await container.get(IFactExtractor)
    facts: CaseFacts = await lexicon.extract(case.text, RU)
    assert {item.term: item.quote for item in facts.manifestations} == case.manifestations
    assert {item.term: item.quote for item in facts.stressors} == case.stressors


async def test_unrecognized_story_is_preserved_in_the_summary(service: Service) -> None:
    story: str = "Внутри как будто поменялась погода"
    summary: SummaryView | None = (
        await service.converse([UserMessage(text=story)], finish=True)
    ).summary
    assert summary is not None
    assert not summary.case.manifestations
    assert summary.case.unrecognized == (story,)
