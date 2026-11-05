"""Проверка ответов системы: для ответа X — ожидаемые нарушения Y.

Случаи из `data/guard_cases.yaml`. Отдельно проверяется, что в собственных
текстах системы из `locales/` нарушений нет.
"""

import asyncio
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
import yaml

from anamnesis.domain.enums.urgency_level import UrgencyLevel
from anamnesis.domain.enums.violation_kind import ViolationKind
from anamnesis.domain.types import LanguageCode
from anamnesis.infrastructure.localization.locale import Locale, load_locales
from anamnesis.infrastructure.safety.reply_guard import LexiconReplyGuard


ROOT = Path(__file__).parents[2]
LOCALES = load_locales(ROOT / "locales")
GUARD = LexiconReplyGuard(LOCALES)
CASES: dict[str, list[dict[str, Any]]] = yaml.safe_load(
    (Path(__file__).parent / "data" / "guard_cases.yaml").read_text(encoding="utf-8"),
)


def level(name: str | None) -> UrgencyLevel | None:
    return UrgencyLevel[name] if name is not None else None


def kinds(text: str, language: LanguageCode, computed: UrgencyLevel | None) -> list[str]:
    violations = asyncio.run(GUARD.check(text, language, computed))
    return sorted({violation.kind for violation in violations})


def locale_texts(locale: Locale) -> Iterator[tuple[str, str, UrgencyLevel | None, bool]]:
    """Тексты системы: где лежит, текст, уровень показа и проверять ли уровень.

    Формулировки уровня и подсказки о специалисте показываются при своём
    уровне; остальные тексты — при любом, поэтому уровень в них не проверяется.
    """
    messages = locale.messages
    for key, text in [*messages.levels.items(), *messages.specialists.items()]:
        yield key, text, level(None if key == "insufficient_data" else key), True
    plain: dict[str, str] = {
        "greeting": messages.greeting,
        "crisis_message": messages.crisis_message,
        "support_others": messages.support_others,
        "disclaimer": messages.disclaimer,
        "refuse": messages.refuse,
        **{f"replies.{stage}": text for stage, text in messages.replies.items()},
        **{f"referrals.{code}": text for code, text in messages.referrals.items()},
        **{f"rules.{rule}": text for rule, text in messages.rules.items()},
        **{f"helplines.{item.phone}": f"{item.name}. {item.note}" for item in messages.helplines},
        **{f"terms.{term}": text for term, text in locale.terms.names.items()},
        **{f"descriptions.{term}": text for term, text in locale.terms.descriptions.items()},
    }
    for fact, question in messages.questions.items():
        plain[f"questions.{fact}"] = question.text
        if question.follow_up is not None:
            plain[f"questions.{fact}.follow_up"] = question.follow_up
        for code, label in question.options.items():
            plain[f"questions.{fact}.{code}"] = label
    for key, text in plain.items():
        yield key, text, None, False


@pytest.mark.parametrize("case", CASES["replies"], ids=lambda case: case["text"][:40])
def test_reply(case: dict[str, Any]) -> None:
    assert kinds(case["text"], LanguageCode("ru"), level(case["level"])) == sorted(case["kinds"])


@pytest.mark.parametrize("language", sorted(LOCALES))
def test_system_texts_have_no_violations(language: LanguageCode) -> None:
    found: dict[str, list[ViolationKind]] = {}
    for key, text, computed, check_level in locale_texts(LOCALES[language]):
        violations = asyncio.run(GUARD.check(text, language, computed))
        relevant = [
            violation.kind
            for violation in violations
            if check_level or violation.kind is not ViolationKind.LEVEL_MISMATCH
        ]
        if relevant:
            found[key] = relevant

    assert found == {}
