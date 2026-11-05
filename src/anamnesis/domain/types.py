from typing import NewType


TermId = NewType("TermId", str)
"""Имя индивида онтологии."""

RuleId = NewType("RuleId", str)
"""Имя индивида класса `InferenceRule` онтологии: `R01`–`R34`."""

OptionCode = NewType("OptionCode", str)
"""Код варианта ответа: `about_month`, `work_and_study`, `refuse`."""
