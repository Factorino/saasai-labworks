from enum import StrEnum, auto


class StatusCode(StrEnum):
    APPLICATION_ERROR = auto()

    NOT_FOUND_ERROR = auto()

    UNSUPPORTED_LANGUAGE_ERROR = auto()
    UNKNOWN_TERM_ERROR = auto()

    LANGUAGE_MODEL_UNAVAILABLE_ERROR = auto()
    LANGUAGE_MODEL_REPLY_ERROR = auto()
