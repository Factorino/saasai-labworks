from collections.abc import Generator, Iterable
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

from owlready2 import World, sync_reasoner_pellet

from anamnesis.domain.types import RuleId, TermId


REPRESENTATIVE_SUFFIX: Final[str] = "_"
"""Индивид-представитель понятия называется по классу с `_` на конце."""


@dataclass(frozen=True, slots=True)
class OntologyNames:
    """Имена индивидов онтологии, которым нужны тексты.

    Attributes:
        rules: Правила (`InferenceRule`): объяснения — в `rules` сообщений.
        terms: Остальные индивиды, кроме направлений: названия — в `terms.yaml`.
    """

    rules: frozenset[RuleId]
    terms: frozenset[TermId]


@contextmanager
def open_ontology(path: Path) -> Generator[Any]:
    world: Any = World()
    try:
        yield world.get_ontology(path.resolve().as_uri()).load()
    finally:
        world.close()


def run_pellet(ontology: Any) -> None:
    sync_reasoner_pellet(
        ontology.world,
        infer_property_values=True,
        infer_data_property_values=True,
        debug=0,
    )


def representatives(individuals: Iterable[Any]) -> frozenset[TermId]:
    names: frozenset[TermId] = frozenset(
        TermId(individual.name)
        for individual in individuals
        if individual.name.endswith(REPRESENTATIVE_SUFFIX)
    )
    return names


def read_names(path: Path) -> OntologyNames:
    """Имена правил и понятий онтологии; у направлений свои тексты, они не входят."""
    with open_ontology(path) as ontology:
        rules: frozenset[RuleId] = frozenset(
            RuleId(rule.name) for rule in ontology.InferenceRule.instances()
        )
        referrals: frozenset[str] = frozenset(
            referral.name for referral in ontology.Referral.instances()
        )
        terms: frozenset[TermId] = frozenset(
            TermId(individual.name)
            for individual in ontology.individuals()
            if individual.name not in rules | referrals
        )

    names: OntologyNames = OntologyNames(rules=rules, terms=terms)
    return names
