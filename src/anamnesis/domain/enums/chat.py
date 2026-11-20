from enum import StrEnum, auto


class MessageRole(StrEnum):
    """Кто автор реплики в диалоге.

    Attributes:
        USER: Человек, который обращается за помощью.
        ASSISTANT: Ассистент.
    """

    USER = auto()
    ASSISTANT = auto()


class ChatStage(StrEnum):
    """Этап сценария диалога.

    Attributes:
        STORY: Свободный рассказ о том, что беспокоит.
        CLARIFYING: Уточняющие вопросы.
        FINISHED: Пользователь досрочно прекратил вопросы.
        SUMMARY: Сводка выдана, дальше свободное общение.
        CRISIS: Кризисный сценарий; выхода из него нет.
    """

    STORY = auto()
    CLARIFYING = auto()
    FINISHED = auto()
    SUMMARY = auto()
    CRISIS = auto()
