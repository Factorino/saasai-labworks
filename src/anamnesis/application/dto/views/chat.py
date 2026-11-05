from datetime import datetime

from anamnesis.application.dto.base import DTO
from anamnesis.domain.entities.chat import ChatId
from anamnesis.domain.enums.chat_stage import ChatStage
from anamnesis.domain.types import LanguageCode


class ChatView(DTO):
    id: ChatId
    language: LanguageCode
    stage: ChatStage
    created_at: datetime
