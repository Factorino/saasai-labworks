from dishka import AsyncContainer, Provider, make_async_container
from dishka.integrations.fastapi import FastapiProvider

from anamnesis.main.config.api import APIConfig
from anamnesis.main.config.config import Config
from anamnesis.main.config.knowledge import KnowledgeConfig
from anamnesis.main.config.server import ServerConfig
from anamnesis.main.config.service import ServiceConfig
from anamnesis.main.di.providers.common import CommonProvider
from anamnesis.main.di.providers.config import ConfigProvider
from anamnesis.main.di.providers.interactors import InteractorsProvider
from anamnesis.main.di.providers.knowledge import KnowledgeProvider


def create_container(config: Config) -> AsyncContainer:
    providers: list[Provider] = [
        FastapiProvider(),
        ConfigProvider(),
        CommonProvider(),
        KnowledgeProvider(),
        InteractorsProvider(),
    ]

    context: dict[type, object] = {
        Config: config,
        ServiceConfig: config.service,
        ServerConfig: config.server,
        APIConfig: config.api,
        KnowledgeConfig: config.knowledge,
    }

    return make_async_container(*providers, context=context)
