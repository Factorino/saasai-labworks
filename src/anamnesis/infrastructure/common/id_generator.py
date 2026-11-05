from typing import override
from uuid import uuid4

from anamnesis.application.interfaces.common.id_generator import IIdGenerator
from anamnesis.domain.entities.chat import ChatId


class ChatIdGenerator(IIdGenerator[ChatId]):
    @override
    def generate(self) -> ChatId:
        return ChatId(uuid4())
