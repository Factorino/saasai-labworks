from typing import ClassVar

from anamnesis.domain.errors.base import DomainError, error
from anamnesis.domain.errors.status_code import StatusCode


@error
class ConsentRequiredError(DomainError):
    code: ClassVar[str] = StatusCode.CONSENT_REQUIRED
    msg: str = "The dialogue cannot start without consent to data processing"


@error
class ChatStageError(DomainError):
    code: ClassVar[str] = StatusCode.CHAT_STAGE_ERROR
    msg: str = "Cannot {action} at the {stage} stage"

    action: str
    stage: str
