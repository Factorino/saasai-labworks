"""Настоящая языковая модель: связь и время отклика; без модели тесты пропускаются."""

import asyncio
import logging
import time

import pytest

from anamnesis.application.commands.chat.finish_chat import FinishChatRequest
from anamnesis.application.commands.chat.start_chat import StartChatRequest
from anamnesis.application.dto.generation import AnswerReply
from anamnesis.application.interfaces.llm.language_model import ModelRequest
from anamnesis.application.services.model_data import data_message
from anamnesis.domain.enums.chat_stage import ChatStage
from anamnesis.infrastructure.llm.openai_model import OpenAICompatibleModel
from anamnesis.main.config.config import Config
from tests.integration.harness import CATALOG, RU, build_service, post


pytestmark = [pytest.mark.llm, pytest.mark.slow, pytest.mark.timeout(300)]

CLARIFYING_LIMIT = 8.0
SUMMARY_LIMIT = 20.0
STORY = (
    "Последние пару месяцев мне тревожно почти постоянно, плохо сплю, просыпаюсь в четыре утра "
    "и больше не могу уснуть. На работе завал, начальник давит, дедлайны каждую неделю, всё "
    "валится из рук. С партнёром постоянно ругаемся из-за денег. Ем через силу, сил ни на что "
    "нет. Хочу понять, что со мной и как к этому подступиться."
)
PING = ModelRequest(
    instruction='Reply with a JSON object whose "text" field holds the word "ok".',
    messages=(data_message({"task": "ping"}),),
)


def live_model() -> OpenAICompatibleModel:
    settings = Config.load().llm
    return OpenAICompatibleModel(
        base_url=settings.base_url,
        api_key=settings.api_key.get_secret_value(),
        model=settings.model,
        temperature=settings.temperature,
        max_tokens=settings.max_tokens,
        reasoning_effort=settings.reasoning_effort,
        connect_timeout=settings.connect_timeout,
        request_timeout=settings.request_timeout,
        max_retries=settings.max_retries,
    )


def test_model_answers_by_schema() -> None:
    async def call() -> AnswerReply:
        model = live_model()
        try:
            return await model.complete_structured(PING, AnswerReply)
        finally:
            await model.close()

    assert asyncio.run(call()).text


def test_response_time(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.WARNING)

    async def scenario() -> tuple[float, float, str]:
        model = live_model()
        service = build_service(model)
        try:
            await model.complete_structured(PING, AnswerReply)
            chat = (await service.start.execute(StartChatRequest(consent=True, language=RU))).chat
            started = time.monotonic()
            story = await post(service, chat.id, STORY)
            clarifying = time.monotonic() - started
            assert story.stage is ChatStage.CLARIFYING
            started = time.monotonic()
            reply = (await service.finish.execute(FinishChatRequest(chat_id=chat.id))).reply
            assert reply.summary is not None
            return clarifying, time.monotonic() - started, reply.summary.description
        finally:
            await model.close()

    clarifying, summary, description = asyncio.run(scenario())

    assert "falls back" not in caplog.text
    assert description != CATALOG.fallback_description(RU)
    assert clarifying <= CLARIFYING_LIMIT
    assert summary <= SUMMARY_LIMIT
