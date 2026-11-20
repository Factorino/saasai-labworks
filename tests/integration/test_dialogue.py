from typing import TYPE_CHECKING

from dishka import AsyncContainer
import pytest

from anamnesis.domain.enums.chat import ChatStage
from anamnesis.domain.enums.crisis import SelfHarmScreening
from anamnesis.domain.enums.fact_kind import FactKind
from anamnesis.domain.enums.recommendation import UrgencyLevel
from anamnesis.main.config.config import Config
from anamnesis.main.config.knowledge import KnowledgeConfig
from anamnesis.main.di.container import create_container
from tests.integration.support.model import ScriptedModel, model_provider
from tests.integration.support.service import Service


if TYPE_CHECKING:
    from anamnesis.application.dto.views.question import QuestionView
    from anamnesis.application.dto.views.reply import ReplyView
    from anamnesis.domain.entities.chat import ChatId


async def test_refused_screening_is_repeated_once_when_rules_request_help(
    service: Service,
    container: AsyncContainer,
) -> None:
    chat: ChatId = await service.start()
    reply: ReplyView = await service.post(chat, "У меня мрачные мысли о смерти")
    screening_questions: list[str] = []
    limit: int = (await container.get(KnowledgeConfig)).question_limit
    for _ in range(limit + 1):
        assert reply.question is not None
        if reply.question.fact is FactKind.SELF_HARM:
            screening_questions.append(reply.question.text)
        reply = await service.post(chat, options=["refuse"])
    assert len(screening_questions) == 2
    assert screening_questions[0] != screening_questions[1]
    assert reply.stage is ChatStage.SUMMARY
    assert reply.summary is not None
    assert reply.summary.case.self_harm is SelfHarmScreening.UNKNOWN
    assert reply.summary.helplines
    assert "R30" in {rule.rule for rule in reply.summary.explanation}


@pytest.mark.parametrize("answer", ["active", "plan"])
async def test_screening_survives_zero_question_limit(answer: str, model: ScriptedModel) -> None:
    config: Config = Config.model_construct(knowledge=KnowledgeConfig(question_limit=0))
    async with create_container(config, model_provider(model)) as container:
        service: Service = Service(container)
        chat: ChatId = await service.start()
        reply: ReplyView = await service.post(chat, "Мне тревожно")
        assert reply.question is not None
        assert reply.question.fact is FactKind.SELF_HARM

        model.reset()
        screened: ReplyView = await service.post(chat, options=[answer])
        assert screened.stage is ChatStage.CRISIS
        assert screened.summary is not None
        assert screened.summary.level is UrgencyLevel.L3
        assert screened.summary.helplines
        assert not model.requests


async def test_early_summary_distinguishes_answered_and_missing_facts(service: Service) -> None:
    chat: ChatId = await service.start()
    question: QuestionView | None = (await service.post(chat, "Мне тревожно")).question
    assert question is not None
    assert question.fact is FactKind.DURATION
    await service.post(chat, options=["about_month"])
    reply: ReplyView = await service.finish(chat)

    assert reply.stage is ChatStage.SUMMARY
    assert reply.question is None
    assert reply.summary is not None
    assert reply.summary.case.duration_weeks == 4
    assert set(reply.summary.missing) == {FactKind.FREQUENCY, FactKind.IMPACT, FactKind.SELF_HARM}


async def test_only_screening_can_exceed_the_question_limit(model: ScriptedModel) -> None:
    config: Config = Config.model_construct(knowledge=KnowledgeConfig(question_limit=1))
    async with create_container(config, model_provider(model)) as container:
        service: Service = Service(container)
        chat: ChatId = await service.start()
        reply: ReplyView = await service.post(chat, "Мне тревожно")
        assert reply.question is not None
        assert reply.question.fact is FactKind.DURATION
        screening: QuestionView | None = (
            await service.post(chat, options=["about_week"])
        ).question
        assert screening is not None
        assert screening.fact is FactKind.SELF_HARM
        reply = await service.post(chat, options=["none"])
        assert reply.stage is ChatStage.SUMMARY
        assert reply.summary is not None
        assert reply.summary.case.self_harm is SelfHarmScreening.NONE
