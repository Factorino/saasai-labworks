from typing import TYPE_CHECKING, Final

from dishka import AsyncContainer
import pytest

from anamnesis.application.interfaces.localization.dialogue_texts import IDialogueTexts
from anamnesis.application.interfaces.safety.crisis_detector import ICrisisDetector
from anamnesis.domain.enums.chat import ChatStage
from anamnesis.domain.enums.crisis import CrisisCategory
from anamnesis.infrastructure.filesystem.yaml_reader import YamlFile
from tests.integration.support.cases import LevelName, UserMessage, read_cases
from tests.integration.support.model import ScriptedModel
from tests.integration.support.service import RU, Service


if TYPE_CHECKING:
    from anamnesis.application.dto.views.reply import ReplyView
    from anamnesis.application.dto.views.summary import SummaryView
    from anamnesis.domain.entities.chat import ChatId
    from anamnesis.domain.value_objects.crisis_signal import CrisisSignal


class Utterance(YamlFile):
    text: str
    categories: frozenset[CrisisCategory]


class Dialogue(YamlFile):
    name: str
    messages: tuple[UserMessage, ...]
    stage_before_crisis: ChatStage | None = None
    finish: bool = False
    stage: ChatStage
    level: LevelName | None = None
    crisis_message: bool
    helplines: bool
    support_others: bool
    categories: frozenset[CrisisCategory]


class Cases(YamlFile):
    replies: tuple[Utterance, ...]
    dialogues: tuple[Dialogue, ...]


CASES: Final[Cases] = read_cases("crisis_cases", Cases)


@pytest.mark.parametrize("case", [pytest.param(case, id=case.text) for case in CASES.replies])
async def test_crisis_lexicon(case: Utterance, container: AsyncContainer) -> None:
    detector: ICrisisDetector = await container.get(ICrisisDetector)
    signals: tuple[CrisisSignal, ...] = await detector.detect(case.text, RU)
    assert {signal.category for signal in signals} == case.categories
    assert all(signal.quote and signal.quote in case.text for signal in signals)


@pytest.mark.slow
@pytest.mark.parametrize("case", [pytest.param(case, id=case.name) for case in CASES.dialogues])
async def test_dialogue(
    case: Dialogue, service: Service, model: ScriptedModel, container: AsyncContainer
) -> None:
    if case.stage_before_crisis is None:
        reply: ReplyView = await service.converse(case.messages, finish=case.finish)
    else:
        chat: ChatId = await service.start()
        stage: ChatStage = ChatStage.STORY
        for message in case.messages[:-1]:
            stage = (await service.post(chat, message.text, message.options)).stage
        assert stage is case.stage_before_crisis
        model.reset()
        reply = await service.post(chat, case.messages[-1].text)
        assert not model.requests
        texts: IDialogueTexts = await container.get(IDialogueTexts)
        assert reply.message == texts.crisis_message(RU)

    summary: SummaryView | None = reply.summary
    assert summary is not None
    assert reply.stage == case.stage
    assert summary.crisis is (case.stage is ChatStage.CRISIS)
    if case.level is not None:
        assert summary.level == case.level
    assert bool(reply.message) is case.crisis_message
    assert bool(summary.helplines) is case.helplines
    assert bool(summary.support_others) is case.support_others
    assert {signal.category for signal in summary.signals} == case.categories
