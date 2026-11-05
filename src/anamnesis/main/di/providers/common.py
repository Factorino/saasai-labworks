from dishka import BaseScope, Provider, Scope, provide

from anamnesis.application.interfaces.common.clock import IClock
from anamnesis.application.interfaces.common.id_generator import IIdGenerator
from anamnesis.application.interfaces.repositories.chat import IChatRepository
from anamnesis.domain.entities.chat import ChatId
from anamnesis.infrastructure.common.clock import SystemClock
from anamnesis.infrastructure.common.id_generator import ChatIdGenerator
from anamnesis.infrastructure.persistence.chat_repository import InMemoryChatRepository


class CommonProvider(Provider):
    scope: BaseScope | None = Scope.APP

    @provide
    def clock(self) -> IClock:
        return SystemClock()

    @provide
    def chat_id_generator(self) -> IIdGenerator[ChatId]:
        return ChatIdGenerator()

    @provide
    def chat_repository(self) -> IChatRepository:
        return InMemoryChatRepository()
