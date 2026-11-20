from dishka import BaseScope, Provider, Scope, provide
from dishka.dependency_source import CompositeDependencySource

from anamnesis.application.interfaces.extraction.estimate_extractor import IEstimateExtractor
from anamnesis.application.interfaces.extraction.fact_extractor import IFactExtractor
from anamnesis.application.interfaces.extraction.fact_normalizer import IFactNormalizer
from anamnesis.application.services.extraction import FactExtraction
from anamnesis.infrastructure.extraction.lexicon_estimator import LexiconEstimateExtractor
from anamnesis.infrastructure.extraction.lexicon_extractor import LexiconFactExtractor
from anamnesis.infrastructure.fuzzy.normalizer import FuzzyFactNormalizer
from anamnesis.infrastructure.fuzzy.variables import LinguisticVariables
from anamnesis.infrastructure.text.language import LanguageProfiles
from anamnesis.main.config.knowledge import KnowledgeConfig


class ExtractionProvider(Provider):
    scope: BaseScope | None = Scope.APP

    extraction: CompositeDependencySource = provide(FactExtraction)

    @provide
    def lexicon(self, config: KnowledgeConfig, profiles: LanguageProfiles) -> IFactExtractor:
        return LexiconFactExtractor.load(config.resources_dir, profiles)

    @provide
    def estimator(
        self,
        config: KnowledgeConfig,
        profiles: LanguageProfiles,
        variables: LinguisticVariables,
    ) -> IEstimateExtractor:
        return LexiconEstimateExtractor.load(config.resources_dir, profiles, variables)

    @provide
    def normalizer(self, variables: LinguisticVariables) -> IFactNormalizer:
        return FuzzyFactNormalizer(variables)
