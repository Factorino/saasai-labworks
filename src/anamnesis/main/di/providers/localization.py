from dishka import BaseScope, Provider, Scope, provide

from anamnesis.application.interfaces.knowledge.knowledge_base import IKnowledgeBase
from anamnesis.application.interfaces.localization.concept_texts import IConceptTexts
from anamnesis.application.interfaces.localization.dialogue_texts import IDialogueTexts
from anamnesis.application.interfaces.localization.summary_texts import ISummaryTexts
from anamnesis.application.services.languages import SupportedLanguages
from anamnesis.domain.services.questionnaire import Questionnaire
from anamnesis.infrastructure.knowledge.knowledge_base import YamlKnowledgeBase
from anamnesis.infrastructure.localization.catalog import TextCatalogs
from anamnesis.infrastructure.localization.texts import (
    YamlConceptTexts,
    YamlDialogueTexts,
    YamlSummaryTexts,
)
from anamnesis.infrastructure.text.language import LanguageProfiles
from anamnesis.main.config.knowledge import KnowledgeConfig


class LocalizationProvider(Provider):
    """Языки из настроек и всё, что загружается по ним: тексты, справка, профили языков."""

    scope: BaseScope | None = Scope.APP

    @provide
    def languages(self, config: KnowledgeConfig) -> SupportedLanguages:
        return SupportedLanguages(config.languages)

    @provide
    def catalogs(self, config: KnowledgeConfig, questionnaire: Questionnaire) -> TextCatalogs:
        return TextCatalogs.load(config.locales_dir, config.languages, questionnaire)

    @provide
    def dialogue_texts(self, catalogs: TextCatalogs) -> IDialogueTexts:
        return YamlDialogueTexts(catalogs)

    @provide
    def summary_texts(self, catalogs: TextCatalogs) -> ISummaryTexts:
        return YamlSummaryTexts(catalogs)

    @provide
    def concept_texts(self, catalogs: TextCatalogs) -> IConceptTexts:
        return YamlConceptTexts(catalogs)

    @provide
    def knowledge_base(self, config: KnowledgeConfig) -> IKnowledgeBase:
        return YamlKnowledgeBase.load(config.locales_dir, config.languages)

    @provide
    def profiles(self, config: KnowledgeConfig) -> LanguageProfiles:
        return LanguageProfiles.load(config.resources_dir, config.languages)
