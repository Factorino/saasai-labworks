from enum import StrEnum, auto


class StatusCode(StrEnum):
    APP_ERROR = auto()

    DOMAIN_ERROR = auto()
    VALIDATION_ERROR = auto()

    CONSENT_REQUIRED = auto()
    CHAT_STAGE_ERROR = auto()
