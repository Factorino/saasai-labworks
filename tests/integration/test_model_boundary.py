from typing import TYPE_CHECKING, Final

from dishka import AsyncContainer
from pydantic import Field
import pytest

from anamnesis.application.dto.extraction import ExtractionReply
from anamnesis.application.dto.generation import NarrativeReply
from anamnesis.application.errors.llm import LanguageModelUnavailableError
from anamnesis.application.interfaces.localization.summary_texts import ISummaryTexts
from anamnesis.application.services.extraction import FactExtraction
from anamnesis.domain.enums.fact_kind import FactKind
from anamnesis.domain.enums.recommendation import UrgencyLevel
from anamnesis.infrastructure.filesystem.yaml_reader import YamlFile
from tests.integration.support.cases import ImpactName, read_cases
from tests.integration.support.model import ScriptedModel, ScriptedReply
from tests.integration.support.service import RU, Service


if TYPE_CHECKING:
    from anamnesis.application.dto.views.reply import ReplyView
    from anamnesis.application.dto.views.summary import SummaryView
    from anamnesis.domain.entities.chat import ChatId
    from anamnesis.domain.value_objects.case_facts import CaseFacts


class Case(YamlFile):
    name: str
    text: str
    question: FactKind | None = None
    reply: dict[str, object]
    manifestations: dict[str, str] = Field(default_factory=dict)
    other: tuple[str, ...] = ()
    impact: ImpactName | None = None


class Cases(YamlFile):
    cases: tuple[Case, ...]


EMPTY_REPLY: Final[ExtractionReply] = ExtractionReply(
    manifestations=(),
    stressors=(),
    other=(),
    duration=None,
    frequency=None,
    impact=None,
    goal=None,
)


@pytest.mark.parametrize(
    "case",
    [pytest.param(case, id=case.name) for case in read_cases("extraction_cases", Cases).cases],
)
async def test_extraction(case: Case, container: AsyncContainer, model: ScriptedModel) -> None:
    extraction: FactExtraction = await container.get(FactExtraction)
    model.script(ExtractionReply, EMPTY_REPLY.model_dump() | case.reply)
    facts: CaseFacts = await extraction.extract(RU, case.text, case.question)

    assert len(model.requests_for(ExtractionReply)) == 1
    assert {item.term: item.quote for item in facts.manifestations} == case.manifestations
    assert facts.unrecognized == case.other
    assert facts.impact == case.impact


@pytest.mark.parametrize(
    "failure",
    [
        pytest.param(
            LanguageModelUnavailableError(model="scripted", reason="offline"), id="unavailable"
        ),
        pytest.param(
            LanguageModelUnavailableError(model="scripted", reason="request timed out"),
            id="timeout",
        ),
        pytest.param({"unexpected": "invalid response"}, id="outside_schema"),
    ],
)
async def test_rules_still_determine_urgency_after_model_failure(
    failure: ScriptedReply, service: Service, model: ScriptedModel, container: AsyncContainer
) -> None:
    model.script(ExtractionReply, failure)
    model.script(NarrativeReply, failure)
    chat: ChatId = await service.start()
    reply: ReplyView = await service.post(chat, "Мне грустно")
    for fact, choice in (
        (FactKind.DURATION, "two_three_weeks"),
        (FactKind.FREQUENCY, "rare"),
        (FactKind.IMPACT, "moderate"),
    ):
        assert reply.question is not None
        assert reply.question.fact is fact
        reply = await service.post(chat, options=[choice])

    summary: SummaryView | None = (await service.finish(chat)).summary
    assert summary is not None
    assert {item.term for item in summary.case.manifestations} == {"feel_sad"}
    # Правило R10: сниженное настроение от двух недель с заметным влиянием даёт L2.
    assert "R10" in {rule.rule for rule in summary.explanation}
    assert summary.level is UrgencyLevel.L2
    texts: ISummaryTexts = await container.get(ISummaryTexts)
    assert summary.description == texts.fallback_description(RU)
    assert summary.specialist_request == texts.fallback_request(RU)
    assert model.requests_for(ExtractionReply)
    assert model.requests_for(NarrativeReply)
