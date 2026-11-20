from collections.abc import Iterator, Mapping
from typing import TYPE_CHECKING

from dishka import AsyncContainer
import pytest

from anamnesis.application.dto.generation import AnswerReply, NarrativeReply
from anamnesis.application.interfaces.knowledge.knowledge_base import IKnowledgeBase
from anamnesis.application.interfaces.localization.dialogue_texts import IDialogueTexts
from anamnesis.application.interfaces.localization.summary_texts import ISummaryTexts
from anamnesis.application.interfaces.safety.reply_guard import IReplyGuard, ViolationKind
from anamnesis.domain.enums.chat import ChatStage
from anamnesis.domain.enums.recommendation import UrgencyLevel
from anamnesis.infrastructure.filesystem.yaml_reader import YamlFile
from anamnesis.infrastructure.localization.catalog import TextCatalogs
from tests.integration.support.cases import LevelName, read_cases
from tests.integration.support.model import ScriptedModel
from tests.integration.support.service import RU, Service


if TYPE_CHECKING:
    from anamnesis.application.dto.views.reply import ReplyView
    from anamnesis.application.interfaces.knowledge.knowledge_base import PracticeGuide
    from anamnesis.application.interfaces.safety.reply_guard import ReplyViolation
    from anamnesis.domain.entities.chat import ChatId
    from anamnesis.infrastructure.localization.catalog import MessagesFile, TextCatalog


class Reply(YamlFile):
    text: str
    level: LevelName | None
    kinds: frozenset[ViolationKind]


class Cases(YamlFile):
    replies: tuple[Reply, ...]


@pytest.mark.parametrize(
    "case", [pytest.param(case, id=case.text) for case in read_cases("guard_cases", Cases).replies]
)
async def test_reply(case: Reply, container: AsyncContainer) -> None:
    guard: IReplyGuard = await container.get(IReplyGuard)
    violations: tuple[ReplyViolation, ...] = await guard.check(case.text, RU, case.level)
    assert {violation.kind for violation in violations} == case.kinds
    assert all(v.quote in case.text for v in violations)


def strings(value: object) -> Iterator[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, Mapping):
        for child in value.values():
            yield from strings(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            yield from strings(child)


async def test_published_texts_pass_the_guard(container: AsyncContainer) -> None:
    guard: IReplyGuard = await container.get(IReplyGuard)
    catalog: TextCatalog = (await container.get(TextCatalogs)).get(RU)
    knowledge: IKnowledgeBase = await container.get(IKnowledgeBase)
    messages: MessagesFile = catalog.messages
    for group in (messages.levels, messages.specialists):
        for key, message in group.items():
            level: UrgencyLevel | None = UrgencyLevel[key] if key != "insufficient_data" else None
            assert not await guard.check(message, RU, level), key

    material: list[str] = [
        *strings(messages.model_dump(exclude={"levels", "specialists"})),
        *strings(catalog.terms.model_dump()),
        *(
            text
            for help_line in knowledge.helplines(RU)
            for text in (help_line.name, help_line.note)
        ),
    ]
    for term in catalog.terms.names:
        guide: PracticeGuide | None = knowledge.practice_guide(RU, term)
        if guide is not None:
            material.extend((*guide.steps, *guide.limits))
    for message in material:
        violations: tuple[ReplyViolation, ...] = await guard.check(message, RU, None)
        assert not [v for v in violations if v.kind is not ViolationKind.LEVEL_MISMATCH], message


class Injection(YamlFile):
    name: str
    message: str
    model: tuple[str, ...]
    expected: str | None
    calls: int


class InjectionCases(YamlFile):
    replies: tuple[Injection, ...]


@pytest.mark.parametrize(
    "case",
    [
        pytest.param(case, id=case.name)
        for case in read_cases("injection_cases", InjectionCases).replies
    ],
)
async def test_guarded_reply(
    case: Injection, service: Service, model: ScriptedModel, container: AsyncContainer
) -> None:
    chat: ChatId = await service.start()
    await service.post(chat, "Мне тревожно и плохо сплю")
    await service.finish(chat)
    model.script(AnswerReply, *({"text": text} for text in case.model))
    reply: ReplyView = await service.post(chat, case.message)

    texts: IDialogueTexts = await container.get(IDialogueTexts)
    assert reply.message == (case.expected or texts.reply(RU, ChatStage.SUMMARY))
    assert len(model.requests_for(AnswerReply)) == case.calls


@pytest.mark.parametrize("invalid_field", ["description", "request"])
async def test_unsafe_narrative_is_replaced_by_safe_summary(
    invalid_field: str, service: Service, model: ScriptedModel, container: AsyncContainer
) -> None:
    chat: ChatId = await service.start()
    await service.post(chat, "Мне тревожно и плохо сплю")
    unsafe: dict[str, str] = {
        "description": "Человек обеспокоен.",
        "request": "Обсудить переживания.",
    }
    unsafe[invalid_field] = "У вас депрессия."
    model.script(NarrativeReply, unsafe, unsafe)
    reply: ReplyView = await service.finish(chat)
    assert reply.summary is not None
    texts: ISummaryTexts = await container.get(ISummaryTexts)
    assert reply.summary.description == texts.fallback_description(RU)
    assert reply.summary.specialist_request == texts.fallback_request(RU)
    assert len(model.requests_for(NarrativeReply)) == 2
