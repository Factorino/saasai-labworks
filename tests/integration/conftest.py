"""Общее для интеграционных тестов: пропуск тестов с пометкой `llm` без модели."""

from functools import cache

from openai import APIError, OpenAI
import pytest

from anamnesis.main.config.config import Config


@cache
def _llm_available() -> bool:
    """Отвечает ли сервер из настроек и есть ли на нём нужная модель."""
    settings = Config.load().llm
    with OpenAI(
        base_url=settings.base_url,
        api_key=settings.api_key.get_secret_value(),
        timeout=settings.connect_timeout,
        max_retries=0,
    ) as client:
        try:
            return settings.model in {model.id for model in client.models.list()}
        except APIError:
            return False


@pytest.fixture(autouse=True)
def require_llm(request: pytest.FixtureRequest) -> None:
    if request.node.get_closest_marker("llm") is not None and not _llm_available():
        pytest.skip("language model is unavailable")
