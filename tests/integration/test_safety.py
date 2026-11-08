"""Кризисный контур: для реплики или диалога X — ожидаемая реакция Y.

Случаи из `data/crisis_cases.yaml`. Реплики проверяются кризисным детектором,
диалоги проходят через сценарии `StartChat`, `PostMessage` и `FinishChat`
с настоящими адаптерами — Pellet, тексты и словари из `locales/`.
"""

import asyncio
from pathlib import Path
from typing import Any

import pytest
import yaml

from anamnesis.application.commands.chat.finish_chat import FinishChatRequest
from anamnesis.application.commands.chat.start_chat import StartChatRequest
from anamnesis.application.dto.views.reply import ReplyView
from anamnesis.domain.enums.urgency_level import UrgencyLevel
from anamnesis.infrastructure.safety.lexicon_detector import LexiconCrisisDetector
from tests.integration.harness import LOCALES, RU, ScriptedModel, Service, build_service, post


pytestmark = [pytest.mark.slow, pytest.mark.timeout(120)]

CASES: dict[str, list[dict[str, Any]]] = yaml.safe_load(
    (Path(__file__).parent / "data" / "crisis_cases.yaml").read_text(encoding="utf-8"),
)


@pytest.fixture
def service() -> Service:
    """Модель недоступна: кризисный контур работает без неё."""
    return build_service(ScriptedModel())


async def run_dialogue(service: Service, case: dict[str, Any]) -> ReplyView:
    """Проходит диалог из случая и возвращает последний ответ системы."""
    chat = (await service.start.execute(StartChatRequest(consent=True, language=RU))).chat
    reply: ReplyView | None = None
    for message in case["messages"]:
        reply = await post(service, chat.id, message.get("text", ""), message.get("options", ()))
    if case.get("finish"):
        reply = (await service.finish.execute(FinishChatRequest(chat_id=chat.id))).reply
    assert reply is not None
    return reply


@pytest.mark.parametrize("case", CASES["replies"], ids=lambda case: case["text"])
def test_reply(case: dict[str, Any]) -> None:
    signals = asyncio.run(LexiconCrisisDetector(LOCALES).detect(case["text"], RU))

    assert sorted({signal.category for signal in signals}) == sorted(case["categories"])


@pytest.mark.parametrize("case", CASES["dialogues"], ids=lambda case: case["name"])
def test_dialogue(case: dict[str, Any], service: Service) -> None:
    reply = asyncio.run(run_dialogue(service, case))
    summary = reply.summary

    assert summary is not None
    assert reply.stage == case["stage"]
    if "level" in case:
        assert summary.level is UrgencyLevel[case["level"]]
    assert (reply.message is not None) is case["crisis_message"]
    assert bool(summary.helplines) is case["helplines"]
    assert (summary.support_others is not None) is case["support_others"]
    assert sorted({signal.category for signal in summary.signals}) == sorted(case["categories"])
