from anamnesis.application.errors.common import NotFoundError
from anamnesis.domain.errors.base import error


@error
class ChatNotFoundError(NotFoundError):
    entity: str = "Chat"


@error
class SummaryNotFoundError(NotFoundError):
    entity: str = "Summary"
    field: str = "chat_id"
