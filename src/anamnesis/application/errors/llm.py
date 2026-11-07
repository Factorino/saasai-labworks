from typing import ClassVar

from anamnesis.application.errors.base import ApplicationError
from anamnesis.application.errors.status_code import StatusCode
from anamnesis.domain.errors.base import error


@error
class LanguageModelUnavailableError(ApplicationError):
    code: ClassVar[str] = StatusCode.LANGUAGE_MODEL_UNAVAILABLE_ERROR
    msg: str = "Language model '{model}' is unavailable: {reason}"

    model: str
    reason: str


@error
class LanguageModelReplyError(ApplicationError):
    code: ClassVar[str] = StatusCode.LANGUAGE_MODEL_REPLY_ERROR
    msg: str = "Language model '{model}' returned an invalid reply: {reason}"

    model: str
    reason: str
