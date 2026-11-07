from typing import Literal

from pydantic import Field, SecretStr

from anamnesis.main.config.base import BaseConfig


class LLMConfig(BaseConfig):
    base_url: str = "http://localhost:11434/v1"
    api_key: SecretStr = SecretStr("unused")
    model: str = "qwen3.5:9b"
    temperature: float = Field(default=0.2, ge=0, le=2)
    max_tokens: int = Field(default=2048, ge=1)
    reasoning_effort: Literal["none", "low", "medium", "high"] | None = "none"
    connect_timeout: float = Field(default=5.0, gt=0)
    request_timeout: float = Field(default=120.0, gt=0)
    max_retries: int = Field(default=1, ge=0)
