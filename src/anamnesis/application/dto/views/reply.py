from anamnesis.application.dto.base import DTO
from anamnesis.application.dto.views.question import QuestionView
from anamnesis.application.dto.views.summary import SummaryView
from anamnesis.domain.enums.chat import ChatStage


class ReplyView(DTO):
    """Ответ системы на действие пользователя.

    Заполнены только поля, нужные на этом шаге: вопрос, сводка или сообщение
    (кризисное или свободный ответ).

    Attributes:
        stage: Этап чата после действия.
        message: Текст сообщения: кризисный шаблон или ответ на свободную реплику.
        question: Следующий уточняющий вопрос.
        summary: Итоговая сводка.
    """

    stage: ChatStage
    message: str | None = None
    question: QuestionView | None = None
    summary: SummaryView | None = None
