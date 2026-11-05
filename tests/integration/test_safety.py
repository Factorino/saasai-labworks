"""Кризисный контур: для реплики или диалога X — ожидаемая реакция Y.

Случаи из `data/crisis_cases.yaml`. Реплики проверяются кризисным детектором,
диалоги проходят через сценарии `StartChat`, `PostMessage` и `FinishChat`
с настоящими адаптерами — Pellet, тексты и словари из `locales/`.
"""

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
import yaml

from anamnesis.application.commands.chat.finish_chat import FinishChat, FinishChatRequest
from anamnesis.application.commands.chat.post_message import PostMessage, PostMessageRequest
from anamnesis.application.commands.chat.start_chat import StartChat, StartChatRequest
from anamnesis.application.dto.views.reply import ReplyView
from anamnesis.application.services.dialogue import DialogueService
from anamnesis.application.services.rendering import ViewRenderer
from anamnesis.domain.enums.urgency_level import UrgencyLevel
from anamnesis.domain.services.assessment import AssessmentService
from anamnesis.domain.services.questionnaire import Questionnaire
from anamnesis.domain.types import LanguageCode
from anamnesis.infrastructure.common.clock import SystemClock
from anamnesis.infrastructure.common.id_generator import ChatIdGenerator
from anamnesis.infrastructure.extraction.lexicon_extractor import LexiconFactExtractor
from anamnesis.infrastructure.localization.locale import load_locales
from anamnesis.infrastructure.localization.text_catalog import YamlTextCatalog
from anamnesis.infrastructure.persistence.chat_repository import InMemoryChatRepository
from anamnesis.infrastructure.reasoning.owl_reasoner import OwlCaseReasoner
from anamnesis.infrastructure.safety.lexicon_detector import LexiconCrisisDetector


pytestmark = [pytest.mark.slow, pytest.mark.timeout(120)]

ROOT = Path(__file__).parents[2]
RU = LanguageCode("ru")
LOCALES = load_locales(ROOT / "locales")
CASES: dict[str, list[dict[str, Any]]] = yaml.safe_load(
    (Path(__file__).parent / "data" / "crisis_cases.yaml").read_text(encoding="utf-8"),
)


@dataclass(frozen=True)
class Service:
    start: StartChat
    post: PostMessage
    finish: FinishChat


@pytest.fixture
def service() -> Service:
    catalog = YamlTextCatalog(LOCALES)
    renderer = ViewRenderer(catalog)
    repository = InMemoryChatRepository()
    dialogue = DialogueService(
        questionnaire=Questionnaire(),
        assessment_service=AssessmentService(),
        reasoner=OwlCaseReasoner(ontology_path=ROOT / "ontology" / "anamnesis.owl"),
        catalog=catalog,
        renderer=renderer,
    )
    return Service(
        start=StartChat(
            chat_repository=repository,
            catalog=catalog,
            renderer=renderer,
            id_generator=ChatIdGenerator(),
            clock=SystemClock(),
        ),
        post=PostMessage(
            chat_repository=repository,
            extractor=LexiconFactExtractor(LOCALES),
            detector=LexiconCrisisDetector(LOCALES),
            dialogue=dialogue,
            catalog=catalog,
            renderer=renderer,
        ),
        finish=FinishChat(chat_repository=repository, dialogue=dialogue),
    )


async def run_dialogue(service: Service, case: dict[str, Any]) -> ReplyView:
    """Проходит диалог из случая и возвращает последний ответ системы."""
    chat = (await service.start.execute(StartChatRequest(consent=True, language=RU))).chat
    reply: ReplyView | None = None
    for message in case["messages"]:
        request = PostMessageRequest.model_validate(
            {
                "chat_id": chat.id,
                "text": message.get("text", ""),
                "option_codes": message.get("options", ()),
            },
        )
        reply = (await service.post.execute(request)).reply
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
