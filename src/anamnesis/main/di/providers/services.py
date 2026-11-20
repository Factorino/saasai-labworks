from dishka import BaseScope, Provider, Scope, provide
from dishka.dependency_source import CompositeDependencySource

from anamnesis.application.services.dialogue import DialogueService
from anamnesis.application.services.generation import TextGeneration
from anamnesis.application.services.rendering import ViewRenderer


class ServicesProvider(Provider):
    scope: BaseScope | None = Scope.APP

    services: CompositeDependencySource = (
        provide(ViewRenderer) + provide(TextGeneration) + provide(DialogueService)
    )
