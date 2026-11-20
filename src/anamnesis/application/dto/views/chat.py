from datetime import datetime

from anamnesis.application.dto.base import DTO
from anamnesis.domain.entities.chat import Chat, ChatId
from anamnesis.domain.enums.chat import ChatStage
from anamnesis.domain.types import LanguageCode


class ChatView(DTO):
    """Чат для клиента API.

    Attributes:
        id: Идентификатор чата.
        language: Язык диалога.
        stage: Текущий этап.
        created_at: Когда начат диалог.
    """

    id: ChatId
    language: LanguageCode
    stage: ChatStage
    created_at: datetime

    @classmethod
    def from_domain(cls, chat: Chat) -> "ChatView":
        return cls(
            id=chat.id,
            language=chat.language,
            stage=chat.stage,
            created_at=chat.created_at,
        )
