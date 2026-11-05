from anamnesis.application.dto.base import DTO
from anamnesis.domain.enums.fact_kind import FactKind
from anamnesis.domain.types import OptionCode


class OptionView(DTO):
    code: OptionCode
    label: str


class QuestionView(DTO):
    fact: FactKind
    text: str
    options: tuple[OptionView, ...]
    multiple: bool
    free_text: bool
