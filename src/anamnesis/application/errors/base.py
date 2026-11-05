from typing import ClassVar

from anamnesis.application.errors.status_code import StatusCode
from anamnesis.domain.errors.base import AppError, error


@error
class ApplicationError(AppError):
    code: ClassVar[str] = StatusCode.APPLICATION_ERROR
    msg: str = "An application error occurred"
