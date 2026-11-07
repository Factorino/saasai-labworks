from collections.abc import AsyncIterator

from dishka import BaseScope, Provider, Scope, provide

from anamnesis.application.interfaces.llm.language_model import ILanguageModel
from anamnesis.infrastructure.llm.openai_model import OpenAICompatibleModel
from anamnesis.main.config.llm import LLMConfig


class LLMProvider(Provider):
    scope: BaseScope | None = Scope.APP

    @provide
    async def language_model(self, config: LLMConfig) -> AsyncIterator[ILanguageModel]:
        model = OpenAICompatibleModel(
            base_url=config.base_url,
            api_key=config.api_key.get_secret_value(),
            model=config.model,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            reasoning_effort=config.reasoning_effort,
            connect_timeout=config.connect_timeout,
            request_timeout=config.request_timeout,
            max_retries=config.max_retries,
        )
        try:
            yield model
        finally:
            await model.close()
