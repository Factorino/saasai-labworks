from collections.abc import Mapping
from typing import Final, override

from anamnesis.application.dto.views.summary import HelplineView
from anamnesis.application.interfaces.localization.text_catalog import ITextCatalog
from anamnesis.domain.enums.chat_stage import ChatStage
from anamnesis.domain.enums.fact_kind import FactKind
from anamnesis.domain.enums.referral import Referral
from anamnesis.domain.enums.urgency_level import UrgencyLevel
from anamnesis.domain.types import LanguageCode, OptionCode, RuleId, TermId
from anamnesis.domain.value_objects.question import REFUSE_OPTION_CODE, Question
from anamnesis.infrastructure.localization.locale import Locale, Messages, QuestionTexts


_INSUFFICIENT_DATA_KEY: Final[str] = "insufficient_data"
"""Ключ формулировки «недостаточно данных» в `levels`."""


class YamlTextCatalog(ITextCatalog):
    """Тексты из файлов `locales/<язык>/`."""

    def __init__(self, locales: Mapping[LanguageCode, Locale]) -> None:
        self._locales: Mapping[LanguageCode, Locale] = locales

    @override
    def supports(self, language: LanguageCode) -> bool:
        return language in self._locales

    @override
    def greeting(self, language: LanguageCode) -> str:
        return self._messages(language).greeting

    @override
    def question(self, question: Question, language: LanguageCode) -> str:
        texts: QuestionTexts = self._messages(language).questions[question.fact]
        if question.follow_up and texts.follow_up is not None:
            return texts.follow_up
        return texts.text

    @override
    def option(self, fact: FactKind, code: OptionCode, language: LanguageCode) -> str:
        messages: Messages = self._messages(language)
        label: str | None = messages.questions[fact].options.get(code)
        if label is not None:
            return label
        if code == REFUSE_OPTION_CODE:
            return messages.refuse
        raise KeyError(f"No label for option '{code}' of '{fact}' in '{language}'")

    @override
    def crisis_message(self, language: LanguageCode) -> str:
        return self._messages(language).crisis_message

    @override
    def support_others(self, language: LanguageCode) -> str:
        return self._messages(language).support_others

    @override
    def helplines(self, language: LanguageCode) -> tuple[HelplineView, ...]:
        return tuple(
            HelplineView(name=helpline.name, phone=helpline.phone, note=helpline.note)
            for helpline in self._messages(language).helplines
        )

    @override
    def approximate(self, fact: FactKind, language: LanguageCode) -> str:
        return self._messages(language).approximate[fact]

    @override
    def disclaimer(self, language: LanguageCode) -> str:
        return self._messages(language).disclaimer

    @override
    def level(self, level: UrgencyLevel | None, language: LanguageCode) -> str:
        return self._messages(language).levels[_level_key(level)]

    @override
    def specialist(self, level: UrgencyLevel | None, language: LanguageCode) -> str:
        return self._messages(language).specialists[_level_key(level)]

    @override
    def referral(self, referral: Referral, language: LanguageCode) -> str:
        return self._messages(language).referrals[referral]

    @override
    def rule(self, rule: RuleId, language: LanguageCode) -> str:
        return self._messages(language).rules[rule]

    @override
    def term(self, term: TermId, language: LanguageCode) -> str:
        return self._locales[language].terms.names.get(term, term)

    @override
    def description(self, term: TermId, language: LanguageCode) -> str:
        return self._locales[language].terms.descriptions.get(term, "")

    @override
    def source(self, term: TermId, language: LanguageCode) -> str | None:
        return self._locales[language].terms.sources.get(term)

    @override
    def reply(self, stage: ChatStage, language: LanguageCode) -> str:
        return self._messages(language).replies[stage]

    def _messages(self, language: LanguageCode) -> Messages:
        return self._locales[language].messages


def _level_key(level: UrgencyLevel | None) -> str:
    """Ключ текстов уровня: `L0`–`L3` или «недостаточно данных»."""
    return level.name if level is not None else _INSUFFICIENT_DATA_KEY
