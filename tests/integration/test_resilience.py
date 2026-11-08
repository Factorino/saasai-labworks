"""Устойчивость к сбоям модели: для ответа или сбоя X — поведение системы Y.

Случаи извлечения — из `data/extraction_cases.yaml`. Перегенерация и безопасный
шаблон проверяются в `test_injection.py`, нечёткая нормализация — в `test_fuzzy.py`.
"""

import asyncio
from collections.abc import Iterator
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import socket
from threading import Thread
import time
from typing import Any, cast, override

import pytest
import yaml

from anamnesis.application.commands.chat.finish_chat import FinishChatRequest
from anamnesis.application.commands.chat.start_chat import StartChatRequest
from anamnesis.application.dto.base import DTO
from anamnesis.application.dto.extraction import ExtractionReply
from anamnesis.application.dto.generation import AnswerReply
from anamnesis.application.errors.llm import (
    LanguageModelReplyError,
    LanguageModelUnavailableError,
)
from anamnesis.application.interfaces.llm.language_model import ILanguageModel, ModelRequest
from anamnesis.domain.enums.chat_stage import ChatStage
from anamnesis.domain.enums.fact_kind import FactKind
from anamnesis.domain.enums.message_role import MessageRole
from anamnesis.domain.value_objects.message import Message
from anamnesis.infrastructure.llm.openai_model import OpenAICompatibleModel
from tests.integration.harness import CATALOG, RU, ScriptedModel, Service, build_service, post


pytestmark = [pytest.mark.slow, pytest.mark.timeout(120)]

CASES: list[dict[str, Any]] = yaml.safe_load(
    (Path(__file__).parent / "data" / "extraction_cases.yaml").read_text(encoding="utf-8"),
)
STORY = "Мне тревожно и плохо сплю"
EMPTY_REPLY: dict[str, Any] = {
    "manifestations": (),
    "stressors": (),
    "other": (),
    "duration": None,
    "frequency": None,
    "impact": None,
    "goal": None,
}
FAILURES = [
    LanguageModelUnavailableError(model="test", reason="down"),
    LanguageModelReplyError(model="test", reason="broken"),
]


class FailingModel(ILanguageModel):
    def __init__(self, error: Exception) -> None:
        self._error: Exception = error

    @override
    async def complete_structured[OutputT: DTO](
        self,
        request: ModelRequest,
        output: type[OutputT],
    ) -> OutputT:
        raise self._error


async def summary_then_talk(service: Service) -> tuple[Any, Any, str | None]:
    chat = (await service.start.execute(StartChatRequest(consent=True, language=RU))).chat
    question = await post(service, chat.id, STORY)
    summary = (await service.finish.execute(FinishChatRequest(chat_id=chat.id))).reply
    answer = (await post(service, chat.id, "Что мне делать дальше?")).message
    return question, summary, answer


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["name"])
def test_invalid_model_output_is_dropped(case: dict[str, Any]) -> None:
    model = ScriptedModel(ExtractionReply(**{**EMPTY_REPLY, **case["reply"]}))
    question = FactKind(case["question"]) if "question" in case else None

    facts = asyncio.run(build_service(model).extraction.extract(case["text"], RU, question))

    assert {item.term: item.quote for item in facts.manifestations} == case.get(
        "manifestations", {}
    )
    assert list(facts.unrecognized) == case.get("other", [])
    assert (facts.impact.name.lower() if facts.impact else None) == case.get("impact")


@pytest.mark.parametrize("error", FAILURES, ids=lambda error: type(error).__name__)
def test_dialogue_survives_model_failure(error: Exception) -> None:
    question, summary, answer = asyncio.run(summary_then_talk(build_service(FailingModel(error))))

    assert question.stage is ChatStage.CLARIFYING
    assert question.question is not None
    assert summary.summary.case.manifestations
    assert summary.summary.description == CATALOG.fallback_description(RU)
    assert answer == CATALOG.reply(ChatStage.SUMMARY, RU)


def test_dialogue_uses_model_again_after_outage() -> None:
    model = ScriptedModel(AnswerReply(text="Модель снова отвечает."))

    _, summary, answer = asyncio.run(summary_then_talk(build_service(model)))

    assert summary.summary.case.manifestations
    assert answer == "Модель снова отвечает."
    assert len(model.requests) == 1


# --- Адаптер против настоящего HTTP-соединения --------------------------------


@dataclass(frozen=True)
class Script:
    body: dict[str, Any]
    status: int = 200
    delay: float = 0.0


def completion(content: str, finish_reason: str = "stop") -> dict[str, Any]:
    return {
        "id": "test",
        "object": "chat.completion",
        "created": 0,
        "model": "test",
        "choices": [
            {
                "index": 0,
                "finish_reason": finish_reason,
                "message": {"role": "assistant", "content": content},
            },
        ],
    }


class ScriptServer(ThreadingHTTPServer):
    script: Script = Script(body={})


class Handler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        script = cast("ScriptServer", self.server).script
        self.rfile.read(int(self.headers["Content-Length"]))
        time.sleep(script.delay)
        body = json.dumps(script.body).encode()
        self.send_response(script.status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        try:
            self.wfile.write(body)
        except OSError:
            self.close_connection = True

    @override
    def log_message(self, format: str, *args: Any) -> None:
        return


@pytest.fixture
def server() -> Iterator[ScriptServer]:
    instance = ScriptServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=instance.serve_forever, daemon=True)
    thread.start()
    yield instance
    instance.shutdown()
    thread.join()
    instance.server_close()


def ask(port: int) -> AnswerReply:
    async def call() -> AnswerReply:
        model = OpenAICompatibleModel(
            base_url=f"http://127.0.0.1:{port}/v1",
            api_key="unused",
            model="test",
            temperature=0.0,
            max_tokens=16,
            reasoning_effort=None,
            connect_timeout=0.2,
            request_timeout=0.2,
            max_retries=0,
        )
        try:
            return await model.complete_structured(
                ModelRequest(
                    instruction="instruction",
                    messages=(Message(role=MessageRole.USER, text="data"),),
                ),
                AnswerReply,
            )
        finally:
            await model.close()

    return asyncio.run(call())


def test_adapter_accepts_reply_by_schema(server: ScriptServer) -> None:
    server.script = Script(completion('{"text": "Ответ"}'))

    assert ask(server.server_address[1]).text == "Ответ"


@pytest.mark.parametrize(
    "script",
    [
        pytest.param(Script(completion("просто текст")), id="not_json"),
        pytest.param(Script(completion('{"answer": "Ответ"}')), id="wrong_field"),
        pytest.param(Script(completion('{"text": "Ответ", "extra": 1}')), id="extra_field"),
        pytest.param(Script(completion('{"text": ""}')), id="empty_text"),
        pytest.param(Script(completion('{"text": "Отв', "length")), id="cut_off"),
        pytest.param(Script(completion("")), id="empty_content"),
    ],
)
def test_adapter_rejects_reply_outside_schema(server: ScriptServer, script: Script) -> None:
    server.script = script

    with pytest.raises(LanguageModelReplyError):
        ask(server.server_address[1])


@pytest.mark.parametrize(
    "script",
    [
        pytest.param(Script(body={}, status=500), id="server_error"),
        pytest.param(Script(completion('{"text": "Поздно"}'), delay=0.6), id="too_slow"),
    ],
)
def test_adapter_reports_unavailable_server(server: ScriptServer, script: Script) -> None:
    server.script = script

    with pytest.raises(LanguageModelUnavailableError):
        ask(server.server_address[1])


def test_adapter_reports_closed_port() -> None:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]

    with pytest.raises(LanguageModelUnavailableError):
        ask(port)
