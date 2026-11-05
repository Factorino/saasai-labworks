from dishka import BaseScope, Provider, Scope, from_context
from dishka.dependency_source import CompositeDependencySource

from anamnesis.main.config.api import APIConfig
from anamnesis.main.config.config import Config
from anamnesis.main.config.knowledge import KnowledgeConfig
from anamnesis.main.config.server import ServerConfig
from anamnesis.main.config.service import ServiceConfig


class ConfigProvider(Provider):
    scope: BaseScope | None = Scope.APP

    configs: CompositeDependencySource = (
        from_context(Config)
        + from_context(ServiceConfig)
        + from_context(ServerConfig)
        + from_context(APIConfig)
        + from_context(KnowledgeConfig)
    )
