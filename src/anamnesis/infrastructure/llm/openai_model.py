from typing import TYPE_CHECKING, override

from openai import (
    APIConnectionError,
    APIStatusError,
    AsyncOpenAI,
    Omit,
    Timeout,
    omit,
)
from openai.types.chat import ChatCompletion, ChatCompletionMessageParam
from openai.types.shared import ReasoningEffort
from openai.types.shared_params import ResponseFormatJSONSchema
import pydantic

from anamnesis.application.dto.base import DTO
from anamnesis.application.errors.llm import (
    LanguageModelReplyError,
    LanguageModelUnavailableError,
)
from anamnesis.application.interfaces.llm.language_model import ILanguageModel, ModelRequest
from anamnesis.domain.enums.message_role import MessageRole


if TYPE_CHECKING:
    from openai.types.chat.chat_completion import Choice


class OpenAICompatibleModel(ILanguageModel):
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        temperature: float,
        max_tokens: int,
        reasoning_effort: ReasoningEffort,
        connect_timeout: float,
        request_timeout: float,
        max_retries: int,
    ) -> None:
        self._client: AsyncOpenAI = AsyncOpenAI(
            base_url=base_url,
            api_key=api_key,
            timeout=Timeout(request_timeout, connect=connect_timeout),
            max_retries=max_retries,
        )
        self._model: str = model
        self._temperature: float = temperature
        self._max_tokens: int = max_tokens
        self._reasoning_effort: ReasoningEffort | Omit = (
            omit if reasoning_effort is None else reasoning_effort
        )

    @property
    def model(self) -> str:
        return self._model

    async def close(self) -> None:
        await self._client.close()

    @override
    async def complete(self, request: ModelRequest) -> str:
        return await self._create(request, omit)

    @override
    async def complete_structured[OutputT: DTO](
        self,
        request: ModelRequest,
        output: type[OutputT],
    ) -> OutputT:
        content: str = await self._create(request, self._response_format(output))
        try:
            return output.model_validate_json(content)
        except pydantic.ValidationError as error:
            first: str = error.errors()[0]["msg"]
            raise LanguageModelReplyError(
                model=self._model,
                reason=f"does not match {output.__name__} ({error.error_count()} errors): {first}",
            ) from error

    async def _create(
        self,
        request: ModelRequest,
        response_format: ResponseFormatJSONSchema | Omit,
    ) -> str:
        try:
            completion: ChatCompletion = await self._client.chat.completions.create(
                model=self._model,
                messages=self._messages(request),
                temperature=(
                    self._temperature if request.temperature is None else request.temperature
                ),
                max_tokens=self._max_tokens,
                reasoning_effort=self._reasoning_effort,
                response_format=response_format,
            )
        except APIConnectionError as error:
            raise LanguageModelUnavailableError(model=self._model, reason=str(error)) from error
        except APIStatusError as error:
            raise LanguageModelUnavailableError(model=self._model, reason=error.message) from error
        return self._content(completion)

    @staticmethod
    def _messages(request: ModelRequest) -> list[ChatCompletionMessageParam]:
        messages: list[ChatCompletionMessageParam] = [
            {"role": "system", "content": request.instruction},
        ]
        for message in request.messages:
            if message.role is MessageRole.USER:
                messages.append({"role": "user", "content": message.text})
            else:
                messages.append({"role": "assistant", "content": message.text})
        return messages

    @staticmethod
    def _response_format(output: type[DTO]) -> ResponseFormatJSONSchema:
        return {
            "type": "json_schema",
            "json_schema": {
                "name": output.__name__,
                "schema": output.model_json_schema(),
                "strict": True,
            },
        }

    def _content(self, completion: ChatCompletion) -> str:
        if not completion.choices:
            raise LanguageModelReplyError(model=self._model, reason="no choices")
        choice: Choice = completion.choices[0]
        if choice.finish_reason == "length":
            raise LanguageModelReplyError(
                model=self._model,
                reason=f"cut off at {self._max_tokens} tokens",
            )
        content: str = (choice.message.content or "").strip()
        if not content:
            raise LanguageModelReplyError(model=self._model, reason="empty content")
        return content
