from typing import ClassVar, Final

from anamnesis.domain.enums.fact_kind import FactKind
from anamnesis.domain.errors.common import ValidationError
from anamnesis.domain.types import OptionCode
from anamnesis.domain.value_objects.base import ValueObject, value_object


REFUSE_OPTION_CODE: Final[OptionCode] = OptionCode("refuse")
"""Код варианта «Не хочу отвечать»"""


@value_object
class Answer(ValueObject):
    """Ответ пользователя на уточняющий вопрос.

    Attributes:
        option_codes: Коды выбранных вариантов без повторов и пустых.
        text: Свободный текст.
    """

    _FIELD_NAME: ClassVar[str] = "Answer"

    option_codes: tuple[OptionCode, ...] = ()
    text: str | None = None

    def __post_init__(self) -> None:
        self._normalize()
        self._validate()

    def _normalize(self) -> None:
        codes: dict[OptionCode, None] = dict.fromkeys(
            OptionCode(code.strip()) for code in self.option_codes
        )
        self._set("option_codes", tuple(code for code in codes if code))
        if self.text is not None:
            self._set("text", self.text.strip() or None)

    def _validate(self) -> None:
        if not self.option_codes and self.text is None:
            raise ValidationError(field=self._FIELD_NAME, reason="must contain an option or text")

    @property
    def is_refusal(self) -> bool:
        """Выбран ли вариант отказа."""
        return REFUSE_OPTION_CODE in self.option_codes


@value_object
class Question(ValueObject):
    """Уточняющий вопрос о сведении одного вида.

    Attributes:
        fact: Какое сведение уточняет вопрос.
        options: Коды вариантов; последний всегда `refuse`.
        multiple: Можно выбрать несколько вариантов (сферы жизни).
        free_text: Можно ответить своими словами: только так (проявления, цель)
            или вместо варианта (длительность, частота, влияние).
        follow_up: Повторный вопрос: варианты те же, формулировка другая.
    """

    _FIELD_NAME: ClassVar[str] = "Question"

    fact: FactKind
    options: tuple[OptionCode, ...]
    multiple: bool = False
    free_text: bool = False
    follow_up: bool = False

    def __post_init__(self) -> None:
        self._validate()

    def _validate(self) -> None:
        if len(self.options) != len(set(self.options)):
            raise ValidationError(field=self._FIELD_NAME, reason="option codes must be unique")
