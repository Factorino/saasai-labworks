from collections.abc import Mapping
import logging
from types import MappingProxyType
from typing import Any, Final

from fastapi import Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from anamnesis.application.errors.common import NotFoundError
from anamnesis.application.errors.knowledge import UnknownTermError, UnsupportedLanguageError
from anamnesis.domain.errors.base import AppError, DomainError
from anamnesis.domain.errors.chat import ChatStageError, ConsentRequiredError
from anamnesis.domain.errors.common import ValidationError


_logger: Final[logging.Logger] = logging.getLogger(__name__)

_ERROR_STATUS_CODE: Final[Mapping[type[AppError], int]] = MappingProxyType(
    {
        ValidationError: status.HTTP_422_UNPROCESSABLE_CONTENT,
        UnknownTermError: status.HTTP_422_UNPROCESSABLE_CONTENT,
        UnsupportedLanguageError: status.HTTP_422_UNPROCESSABLE_CONTENT,
        ConsentRequiredError: status.HTTP_403_FORBIDDEN,
        ChatStageError: status.HTTP_409_CONFLICT,
        DomainError: status.HTTP_400_BAD_REQUEST,
        NotFoundError: status.HTTP_404_NOT_FOUND,
        AppError: status.HTTP_500_INTERNAL_SERVER_ERROR,
    },
)


class ErrorResponse(BaseModel):
    status_code: int
    code: str
    message: str
    detail: dict[str, Any] = Field(default_factory=dict)


async def error_handler(_request: Request, exception: Exception) -> JSONResponse:
    if not isinstance(exception, AppError):
        raise exception

    status_code: int = _status_code(exception)

    response: dict[str, Any] = ErrorResponse(
        status_code=status_code,
        code=exception.code,
        message=str(exception),
        detail=exception.context,
    ).model_dump(mode="json")

    if status_code >= status.HTTP_500_INTERNAL_SERVER_ERROR:
        _logger.error("Request failed: %s", response, exc_info=exception)

    return JSONResponse(status_code=status_code, content=response)


def _status_code(exception: AppError) -> int:
    for cls in type(exception).mro():
        if cls in _ERROR_STATUS_CODE:
            return _ERROR_STATUS_CODE[cls]
    return status.HTTP_500_INTERNAL_SERVER_ERROR
