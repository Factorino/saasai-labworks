from enum import StrEnum, auto


class ChatStage(StrEnum):
    """Этап сценария диалога.

    Согласие проверяется при создании чата, поэтому отдельного этапа для
    него нет.

    Attributes:
        STORY: Свободный рассказ о том, что беспокоит.
        CLARIFYING: Уточняющие вопросы.
        SUMMARY: Сводка выдана, дальше свободное общение.
        CRISIS: Кризисный сценарий; выхода из него нет.
    """

    STORY = auto()
    CLARIFYING = auto()
    SUMMARY = auto()
    CRISIS = auto()
