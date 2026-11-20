from anamnesis.application.dto.base import DTO
from anamnesis.domain.enums.fact_kind import FactKind
from anamnesis.domain.types import OptionCode


class OptionView(DTO):
    """Вариант ответа на уточняющий вопрос.

    Attributes:
        code: Код варианта, который клиент присылает в ответе.
        label: Подпись варианта на языке чата.
    """

    code: OptionCode
    label: str


class QuestionView(DTO):
    """Уточняющий вопрос для клиента API.

    Attributes:
        fact: Какое сведение уточняет вопрос.
        text: Формулировка на языке чата, в том числе повторного вопроса.
        options: Варианты ответа; последний — отказ.
        multiple: Можно выбрать несколько вариантов.
        free_text: Можно ответить своими словами.
    """

    fact: FactKind
    text: str
    options: tuple[OptionView, ...]
    multiple: bool
    free_text: bool
