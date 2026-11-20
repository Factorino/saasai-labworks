from typing import TYPE_CHECKING, Final

from dishka import AsyncContainer
import pytest

from anamnesis.application.queries.assessment.assess_case import AssessCaseRequest
from anamnesis.domain.enums.recommendation import Referral
from anamnesis.domain.types import LanguageCode
from anamnesis.infrastructure.filesystem.yaml_reader import YamlFile
from anamnesis.infrastructure.reasoning.ontology import OntologyNames
from tests.integration.support.cases import LevelName, read_cases
from tests.integration.support.service import RU, Service


if TYPE_CHECKING:
    from anamnesis.application.dto.views.summary import SummaryView


class Case(AssessCaseRequest):
    name: str
    language: LanguageCode = RU

    def request(self) -> AssessCaseRequest:
        return AssessCaseRequest.model_validate(
            self.model_dump(include=set(AssessCaseRequest.model_fields))
        )


class Reference(Case):
    level: LevelName
    rules: tuple[str, ...]
    referrals: tuple[Referral, ...]


class RuleCase(Case):
    rule: str
    fires: bool


class Cases(YamlFile):
    reference: tuple[Reference, ...]
    rules: tuple[RuleCase, ...]


CASES: Final[Cases] = read_cases("ontology_cases", Cases)
pytestmark: pytest.MarkDecorator = pytest.mark.slow


@pytest.mark.parametrize("case", [pytest.param(case, id=case.name) for case in CASES.reference])
async def test_reference_case(case: Reference, service: Service) -> None:
    summary: SummaryView = await service.assess(case.request())

    assert summary.level == case.level
    assert tuple(rule.rule for rule in summary.explanation) == case.rules
    assert tuple(referral.referral for referral in summary.referrals) == case.referrals
    assert all(rule.explanation for rule in summary.explanation)


@pytest.mark.parametrize("case", [pytest.param(case, id=case.name) for case in CASES.rules])
async def test_rule(case: RuleCase, service: Service) -> None:
    summary: SummaryView = await service.assess(case.request())

    assert (case.rule in {rule.rule for rule in summary.explanation}) is case.fires


async def test_every_ontology_rule_has_positive_and_negative_cases(
    container: AsyncContainer,
) -> None:
    names: OntologyNames = await container.get(OntologyNames)
    for expected in (True, False):
        assert {case.rule for case in CASES.rules if case.fires is expected} == names.rules
