from anamnesis.application.dto.base import DTO
from anamnesis.application.dto.views.question import QuestionView
from anamnesis.application.dto.views.summary import SummaryView
from anamnesis.domain.enums.chat_stage import ChatStage


class ReplyView(DTO):
    stage: ChatStage
    message: str | None = None
    question: QuestionView | None = None
    summary: SummaryView | None = None
