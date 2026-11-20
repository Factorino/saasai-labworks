from typing import ClassVar

from anamnesis.domain.errors.base import DomainError, error
from anamnesis.domain.errors.status_code import StatusCode


@error
class ValidationError(DomainError, ValueError, TypeError):
    code: ClassVar[str] = StatusCode.VALIDATION_ERROR
    msg: str = "Invalid {subject}: {reason}"

    subject: str
    reason: str = "invalid value"
