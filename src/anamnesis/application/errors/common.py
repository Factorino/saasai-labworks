from typing import Any, ClassVar

from anamnesis.application.errors.base import ApplicationError
from anamnesis.application.errors.status_code import StatusCode
from anamnesis.domain.errors.base import error


@error
class NotFoundError(ApplicationError):
    code: ClassVar[str] = StatusCode.NOT_FOUND_ERROR
    msg: str = "{entity} with {field}={value} not found"

    entity: str
    field: str = "id"
    value: Any
