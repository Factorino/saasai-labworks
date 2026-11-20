from dishka import AsyncContainer, Provider, make_async_container
from dishka.integrations.fastapi import FastapiProvider

from anamnesis.main.config.api import APIConfig
from anamnesis.main.config.config import Config
from anamnesis.main.config.knowledge import KnowledgeConfig
from anamnesis.main.config.llm import LLMConfig
from anamnesis.main.config.server import ServerConfig
from anamnesis.main.config.service import ServiceConfig
from anamnesis.main.di.providers.common import CommonProvider
from anamnesis.main.di.providers.config import ConfigProvider
from anamnesis.main.di.providers.extraction import ExtractionProvider
from anamnesis.main.di.providers.interactors import InteractorsProvider
from anamnesis.main.di.providers.knowledge import KnowledgeProvider
from anamnesis.main.di.providers.llm import LLMProvider
from anamnesis.main.di.providers.localization import LocalizationProvider
from anamnesis.main.di.providers.safety import SafetyProvider
from anamnesis.main.di.providers.services import ServicesProvider


def create_container(config: Config, *overrides: Provider) -> AsyncContainer:
    """Контейнер приложения; `overrides` подменяют зависимости стандартных провайдеров."""
    providers: list[Provider] = [
        FastapiProvider(),
        ConfigProvider(),
        CommonProvider(),
        LocalizationProvider(),
        KnowledgeProvider(),
        ExtractionProvider(),
        SafetyProvider(),
        LLMProvider(),
        ServicesProvider(),
        InteractorsProvider(),
        *overrides,
    ]

    context: dict[type, object] = {
        Config: config,
        ServiceConfig: config.service,
        ServerConfig: config.server,
        APIConfig: config.api,
        KnowledgeConfig: config.knowledge,
        LLMConfig: config.llm,
    }

    return make_async_container(*providers, context=context)
