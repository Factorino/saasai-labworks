from contextvars import ContextVar, Token
import os
from pathlib import Path
from typing import ClassVar, Final, override

from pydantic import Field
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    TomlConfigSettingsSource,
)

from anamnesis.main.config.api import APIConfig
from anamnesis.main.config.knowledge import KnowledgeConfig
from anamnesis.main.config.llm import LLMConfig
from anamnesis.main.config.server import ServerConfig
from anamnesis.main.config.service import ServiceConfig


CONFIG_FILE_VARIABLE: Final[str] = "CONFIG_FILE"

DEFAULT_CONFIG_FILE: Final[str] = "./.config/local.toml"

_PATH: Final[ContextVar[str | None]] = ContextVar("config_path")


def _resolve_path(path: str | None) -> str | None:
    requested: str | None = path or os.environ.get(CONFIG_FILE_VARIABLE)
    if requested is None:
        return DEFAULT_CONFIG_FILE if Path(DEFAULT_CONFIG_FILE).is_file() else None
    if not Path(requested).is_file():
        raise ValueError(f"Configuration file not found at {requested}")
    return requested


class Config(BaseSettings):
    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        frozen=True,
        extra="forbid",
        env_prefix="APP__",
        env_nested_delimiter="__",
        nested_model_default_partial_update=True,
    )

    service: ServiceConfig = Field(default_factory=ServiceConfig)
    server: ServerConfig = Field(default_factory=ServerConfig)
    api: APIConfig = Field(default_factory=APIConfig)
    knowledge: KnowledgeConfig = Field(default_factory=KnowledgeConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)

    @classmethod
    def load(cls, *, path: str | None = None) -> "Config":
        token: Token[str | None] = _PATH.set(_resolve_path(path))
        try:
            return cls()
        finally:
            _PATH.reset(token)

    @classmethod
    @override
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        try:
            path: str | None = _PATH.get()
        except LookupError:
            path = _resolve_path(None)

        sources: list[PydanticBaseSettingsSource] = [init_settings, env_settings]
        if path is not None:
            sources.append(TomlConfigSettingsSource(settings_cls, toml_file=path))
        return tuple(sources)
