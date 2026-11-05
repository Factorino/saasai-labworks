from collections.abc import Mapping

from dishka import BaseScope, Provider, Scope, provide
from dishka.dependency_source import CompositeDependencySource

from anamnesis.application.interfaces.extraction.fact_extractor import IFactExtractor
from anamnesis.application.interfaces.localization.text_catalog import ITextCatalog
from anamnesis.application.interfaces.reasoning.case_reasoner import ICaseReasoner
from anamnesis.application.interfaces.safety.crisis_detector import ICrisisDetector
from anamnesis.application.services.dialogue import DialogueService
from anamnesis.application.services.rendering import ViewRenderer
from anamnesis.domain.services.assessment import AssessmentService
from anamnesis.domain.services.questionnaire import Questionnaire
from anamnesis.domain.types import LanguageCode
from anamnesis.infrastructure.extraction.lexicon_extractor import LexiconFactExtractor
from anamnesis.infrastructure.localization.locale import Locale, load_locales
from anamnesis.infrastructure.localization.text_catalog import YamlTextCatalog
from anamnesis.infrastructure.reasoning.owl_reasoner import OwlCaseReasoner
from anamnesis.infrastructure.safety.lexicon_detector import LexiconCrisisDetector
from anamnesis.main.config.knowledge import KnowledgeConfig


class KnowledgeProvider(Provider):
    scope: BaseScope | None = Scope.APP

    renderer: CompositeDependencySource = provide(ViewRenderer)
    assessment_service: CompositeDependencySource = provide(AssessmentService)

    @provide
    def locales(self, config: KnowledgeConfig) -> Mapping[LanguageCode, Locale]:
        return load_locales(config.locales_dir)

    @provide
    def catalog(self, locales: Mapping[LanguageCode, Locale]) -> ITextCatalog:
        return YamlTextCatalog(locales)

    @provide
    def extractor(self, locales: Mapping[LanguageCode, Locale]) -> IFactExtractor:
        return LexiconFactExtractor(locales)

    @provide
    def detector(self, locales: Mapping[LanguageCode, Locale]) -> ICrisisDetector:
        return LexiconCrisisDetector(locales)

    @provide
    def reasoner(self, config: KnowledgeConfig) -> ICaseReasoner:
        return OwlCaseReasoner(
            ontology_path=config.ontology_path,
            max_concurrency=config.reasoner_concurrency,
        )

    @provide
    def questionnaire(self, config: KnowledgeConfig) -> Questionnaire:
        return Questionnaire(question_limit=config.question_limit)

    @provide
    def dialogue(
        self,
        questionnaire: Questionnaire,
        assessment_service: AssessmentService,
        reasoner: ICaseReasoner,
        catalog: ITextCatalog,
        renderer: ViewRenderer,
    ) -> DialogueService:
        return DialogueService(
            questionnaire=questionnaire,
            assessment_service=assessment_service,
            reasoner=reasoner,
            catalog=catalog,
            renderer=renderer,
        )
