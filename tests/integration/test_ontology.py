"""Онтология и правила: для случая X — ожидаемый результат оценки Y."""

import asyncio
from pathlib import Path
from typing import Any

import pytest
import yaml

from anamnesis.application.dto.views.summary import SummaryView
from anamnesis.application.queries.assessment.assess_case import AssessCase, AssessCaseRequest
from anamnesis.application.services.rendering import ViewRenderer
from anamnesis.domain.enums.urgency_level import UrgencyLevel
from anamnesis.domain.services.assessment import AssessmentService
from anamnesis.infrastructure.knowledge.practice_selection import load_practice_selection
from anamnesis.infrastructure.localization.locale import load_locales
from anamnesis.infrastructure.localization.text_catalog import YamlTextCatalog
from anamnesis.infrastructure.reasoning.owl_reasoner import OwlCaseReasoner


pytestmark = [pytest.mark.slow, pytest.mark.timeout(300)]

ROOT = Path(__file__).parents[2]

REASONER_CONCURRENCY = 3
CASES: dict[str, list[dict[str, Any]]] = yaml.safe_load(
    (Path(__file__).parent / "data" / "ontology_cases.yaml").read_text(encoding="utf-8"),
)


FACT_FIELDS = (
    "manifestations",
    "stressors",
    "duration_weeks",
    "frequency",
    "impact",
    "self_harm",
)


def request(case: dict[str, Any]) -> AssessCaseRequest:
    return AssessCaseRequest.model_validate(
        {"language": "ru", **{field: case[field] for field in FACT_FIELDS}},
    )


@pytest.fixture(scope="session")
def summaries() -> dict[str, SummaryView]:
    """Сводки всех случаев; считаются один раз и параллельно — Pellet около секунды на вывод."""
    catalog = YamlTextCatalog(load_locales(ROOT / "locales"))
    interactor = AssessCase(
        reasoner=OwlCaseReasoner(
            ontology_path=ROOT / "ontology" / "anamnesis.owl", max_concurrency=REASONER_CONCURRENCY
        ),
        assessment_service=AssessmentService(),
        catalog=catalog,
        renderer=ViewRenderer(
            catalog,
            load_practice_selection(ROOT / "knowledge" / "practice_selection.yaml"),
        ),
    )
    cases = [*CASES["reference"], *CASES["rules"]]

    async def assess_all() -> list[SummaryView]:
        responses = await asyncio.gather(*(interactor.execute(request(case)) for case in cases))
        return [response.summary for response in responses]

    return {
        case["name"]: summary
        for case, summary in zip(cases, asyncio.run(assess_all()), strict=True)
    }


def fired_rules(summary: SummaryView) -> list[str]:
    return sorted(rule.rule for rule in summary.explanation)


@pytest.mark.parametrize("case", CASES["reference"], ids=lambda case: case["name"])
def test_reference_case(case: dict[str, Any], summaries: dict[str, SummaryView]) -> None:
    summary = summaries[case["name"]]

    assert summary.level is UrgencyLevel[case["level"]]
    assert fired_rules(summary) == case["rules"]
    assert [referral.referral for referral in summary.referrals] == case["referrals"]


@pytest.mark.parametrize("case", CASES["rules"], ids=lambda case: case["name"])
def test_rule(case: dict[str, Any], summaries: dict[str, SummaryView]) -> None:
    assert (case["rule"] in fired_rules(summaries[case["name"]])) is case["fires"]
