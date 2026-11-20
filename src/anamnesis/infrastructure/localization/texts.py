from typing import override

from anamnesis.application.interfaces.localization.concept_texts import IConceptTexts
from anamnesis.application.interfaces.localization.dialogue_texts import IDialogueTexts
from anamnesis.application.interfaces.localization.summary_texts import ISummaryTexts
from anamnesis.domain.enums.chat import ChatStage
from anamnesis.domain.enums.fact_kind import FactKind
from anamnesis.domain.enums.recommendation import Referral, UrgencyLevel
from anamnesis.domain.types import LanguageCode, OptionCode, RuleId, TermId
from anamnesis.domain.value_objects.clarification import REFUSE_OPTION_CODE, Question
from anamnesis.infrastructure.localization.catalog import (
    MessagesFile,
    QuestionTexts,
    TextCatalogs,
    level_key,
)


class YamlDialogueTexts(IDialogueTexts):
    """Тексты хода диалога из `locales/<язык>/messages.yaml`."""

    def __init__(self, catalogs: TextCatalogs) -> None:
        self._catalogs: TextCatalogs = catalogs

    @override
    def greeting(self, language: LanguageCode) -> str:
        return self._messages(language).greeting

    @override
    def question(self, language: LanguageCode, question: Question) -> str:
        texts: QuestionTexts = self._messages(language).questions[question.fact]
        if question.follow_up and texts.follow_up is not None:
            return texts.follow_up
        return texts.text

    @override
    def option(self, language: LanguageCode, fact: FactKind, code: OptionCode) -> str:
        messages: MessagesFile = self._messages(language)

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
    def reply(self, language: LanguageCode, stage: ChatStage) -> str:
        return self._messages(language).replies[stage]

    def _messages(self, language: LanguageCode) -> MessagesFile:
        return self._catalogs.get(language).messages


class YamlSummaryTexts(ISummaryTexts):
    """Тексты сводки из `locales/<язык>/messages.yaml`."""

    def __init__(self, catalogs: TextCatalogs) -> None:
        self._catalogs: TextCatalogs = catalogs

    @override
    def level(self, language: LanguageCode, level: UrgencyLevel | None) -> str:
        return self._messages(language).levels[level_key(level)]

    @override
    def specialist(self, language: LanguageCode, level: UrgencyLevel | None) -> str:
        return self._messages(language).specialists[level_key(level)]

    @override
    def referral(self, language: LanguageCode, referral: Referral) -> str:
        return self._messages(language).referrals[referral]

    @override
    def rule(self, language: LanguageCode, rule: RuleId) -> str:
        return self._messages(language).rules[rule]

    @override
    def approximate(self, language: LanguageCode, fact: FactKind) -> str:
        return self._messages(language).approximate[fact]

    @override
    def disclaimer(self, language: LanguageCode) -> str:
        return self._messages(language).disclaimer

    @override
    def fallback_description(self, language: LanguageCode) -> str:
        return self._messages(language).fallback.description

    @override
    def fallback_request(self, language: LanguageCode) -> str:
        return self._messages(language).fallback.request

    @override
    def support_others(self, language: LanguageCode) -> str:
        return self._messages(language).support_others

    def _messages(self, language: LanguageCode) -> MessagesFile:
        return self._catalogs.get(language).messages


class YamlConceptTexts(IConceptTexts):
    """Названия и описания понятий из `locales/<язык>/terms.yaml`."""

    def __init__(self, catalogs: TextCatalogs) -> None:
        self._catalogs: TextCatalogs = catalogs

    @override
    def name(self, language: LanguageCode, term: TermId) -> str:
        return self._catalogs.get(language).terms.names.get(term, term)

    @override
    def description(self, language: LanguageCode, term: TermId) -> str:
        return self._catalogs.get(language).terms.descriptions.get(term, "")
