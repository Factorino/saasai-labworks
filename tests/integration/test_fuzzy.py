"""Нечёткая нормализация: ответ своими словами → значение для правил и уверенность.

Случаи из `data/fuzzy_cases.yaml` проходят словарь `locales/ru/fuzzy.yaml` и
лингвистические переменные из `knowledge/linguistic_variables.yaml`.
"""

import asyncio
from pathlib import Path
from typing import Any

import pytest
import yaml

from anamnesis.domain.enums.fact_kind import FactKind
from anamnesis.domain.types import LanguageCode
from anamnesis.domain.value_objects.case_facts import CaseFacts
from anamnesis.infrastructure.extraction.lexicon_estimator import LexiconEstimateExtractor
from anamnesis.infrastructure.fuzzy.normalizer import FuzzyFactNormalizer
from anamnesis.infrastructure.fuzzy.variables import load_linguistic_variables
from anamnesis.infrastructure.localization.locale import load_locales


ROOT = Path(__file__).parents[2]
VARIABLES = load_linguistic_variables(ROOT / "knowledge" / "linguistic_variables.yaml")
EXTRACTOR = LexiconEstimateExtractor(load_locales(ROOT / "locales"), VARIABLES)
NORMALIZER = FuzzyFactNormalizer(VARIABLES)
CASES: dict[str, list[dict[str, Any]]] = yaml.safe_load(
    (Path(__file__).parent / "data" / "fuzzy_cases.yaml").read_text(encoding="utf-8"),
)
PARAMS = [
    pytest.param(FactKind(fact), case, id=f"{fact}: {case['text']}")
    for fact, cases in CASES.items()
    for case in cases
]


def estimate(text: str, fact: FactKind) -> CaseFacts | None:
    found = asyncio.run(EXTRACTOR.extract(text, fact, LanguageCode("ru")))
    return NORMALIZER.normalize(found) if found is not None else None


def value(facts: CaseFacts, fact: FactKind) -> int | str | None:
    if fact is FactKind.DURATION:
        return facts.duration.weeks if facts.duration is not None else None
    scale = facts.frequency if fact is FactKind.FREQUENCY else facts.impact
    return scale.name.lower() if scale is not None else None


@pytest.mark.parametrize(("fact", "case"), PARAMS)
def test_estimate(fact: FactKind, case: dict[str, Any]) -> None:
    facts = estimate(case["text"], fact)

    if case["value"] is None:
        assert facts is None
        return
    assert facts is not None
    assert value(facts, fact) == case["value"]
    assert facts.confidence.get(fact) == (
        pytest.approx(case["confidence"], abs=0.01) if case["confidence"] is not None else None
    )
