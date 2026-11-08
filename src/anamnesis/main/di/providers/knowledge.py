from collections.abc import Mapping

from dishka import BaseScope, Provider, Scope, provide
from dishka.dependency_source import CompositeDependencySource

from anamnesis.application.interfaces.extraction.estimate_extractor import IEstimateExtractor
from anamnesis.application.interfaces.extraction.fact_extractor import IFactExtractor
from anamnesis.application.interfaces.extraction.fact_normalizer import IFactNormalizer
from anamnesis.application.interfaces.knowledge.vocabulary import IOntologyVocabulary
from anamnesis.application.interfaces.llm.instructions import IInstructions
from anamnesis.application.interfaces.localization.text_catalog import ITextCatalog
from anamnesis.application.interfaces.reasoning.case_reasoner import ICaseReasoner
from anamnesis.application.interfaces.safety.crisis_detector import ICrisisDetector
from anamnesis.application.interfaces.safety.reply_guard import IReplyGuard
from anamnesis.application.services.dialogue import DialogueService
from anamnesis.application.services.extraction import FactExtraction
from anamnesis.application.services.generation import TextGeneration
from anamnesis.application.services.rendering import ViewRenderer
from anamnesis.domain.enums.fact_kind import FactKind
from anamnesis.domain.services.assessment import AssessmentService
from anamnesis.domain.services.practice_selection import PracticeSelection
from anamnesis.domain.services.questionnaire import Questionnaire
from anamnesis.domain.types import LanguageCode
from anamnesis.infrastructure.extraction.lexicon_estimator import LexiconEstimateExtractor
from anamnesis.infrastructure.extraction.lexicon_extractor import LexiconFactExtractor
from anamnesis.infrastructure.fuzzy.linguistic_variable import LinguisticVariable
from anamnesis.infrastructure.fuzzy.normalizer import FuzzyFactNormalizer
from anamnesis.infrastructure.fuzzy.variables import load_linguistic_variables
from anamnesis.infrastructure.knowledge.practice_selection import load_practice_selection
from anamnesis.infrastructure.llm.file_instructions import FileInstructions
from anamnesis.infrastructure.localization.locale import Locale, load_locales
from anamnesis.infrastructure.localization.text_catalog import YamlTextCatalog
from anamnesis.infrastructure.reasoning.owl_reasoner import OwlCaseReasoner
from anamnesis.infrastructure.reasoning.owl_vocabulary import OwlOntologyVocabulary
from anamnesis.infrastructure.safety.lexicon_detector import LexiconCrisisDetector
from anamnesis.infrastructure.safety.reply_guard import LexiconReplyGuard
from anamnesis.main.config.knowledge import KnowledgeConfig


class KnowledgeProvider(Provider):
    scope: BaseScope | None = Scope.APP

    renderer: CompositeDependencySource = provide(ViewRenderer)
    assessment_service: CompositeDependencySource = provide(AssessmentService)
    extraction: CompositeDependencySource = provide(FactExtraction)
    generation: CompositeDependencySource = provide(TextGeneration)
    dialogue: CompositeDependencySource = provide(DialogueService)

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
    def linguistic_variables(
        self,
        config: KnowledgeConfig,
    ) -> Mapping[FactKind, LinguisticVariable]:
        return load_linguistic_variables(config.linguistic_variables_path)

    @provide
    def estimator(
        self,
        locales: Mapping[LanguageCode, Locale],
        variables: Mapping[FactKind, LinguisticVariable],
    ) -> IEstimateExtractor:
        return LexiconEstimateExtractor(locales, variables)

    @provide
    def normalizer(self, variables: Mapping[FactKind, LinguisticVariable]) -> IFactNormalizer:
        return FuzzyFactNormalizer(variables)

    @provide
    def vocabulary(self, config: KnowledgeConfig) -> IOntologyVocabulary:
        return OwlOntologyVocabulary(ontology_path=config.ontology_path)

    @provide
    def instructions(self, config: KnowledgeConfig) -> IInstructions:
        return FileInstructions(config.instructions_dir)

    @provide
    def detector(self, locales: Mapping[LanguageCode, Locale]) -> ICrisisDetector:
        return LexiconCrisisDetector(locales)

    @provide
    def reply_guard(self, locales: Mapping[LanguageCode, Locale]) -> IReplyGuard:
        return LexiconReplyGuard(locales)

    @provide
    def reasoner(self, config: KnowledgeConfig) -> ICaseReasoner:
        return OwlCaseReasoner(
            ontology_path=config.ontology_path,
            max_concurrency=config.reasoner_concurrency,
        )

    @provide
    def practice_selection(self, config: KnowledgeConfig) -> PracticeSelection:
        return load_practice_selection(config.practice_selection_path)

    @provide
    def questionnaire(self, config: KnowledgeConfig) -> Questionnaire:
        return Questionnaire(question_limit=config.question_limit)
