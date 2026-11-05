from typing import ClassVar

from anamnesis.application.errors.base import ApplicationError
from anamnesis.application.errors.status_code import StatusCode
from anamnesis.domain.errors.base import error


@error
class UnsupportedLanguageError(ApplicationError):
    code: ClassVar[str] = StatusCode.UNSUPPORTED_LANGUAGE_ERROR
    msg: str = "Language '{language}' is not supported"

    language: str


@error
class UnknownTermError(ApplicationError):
    code: ClassVar[str] = StatusCode.UNKNOWN_TERM_ERROR
    msg: str = "Term '{term}' is not in the ontology"

    term: str
