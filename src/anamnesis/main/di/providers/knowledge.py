from dishka import BaseScope, Provider, Scope, provide
from dishka.dependency_source import CompositeDependencySource

from anamnesis.application.interfaces.knowledge.vocabulary import IOntologyVocabulary
from anamnesis.application.interfaces.llm.instructions import IInstructions
from anamnesis.application.interfaces.reasoning.case_reasoner import ICaseReasoner
from anamnesis.domain.services.assessment import AssessmentService
from anamnesis.domain.services.practice_selection import PracticeSelection
from anamnesis.domain.services.questionnaire import Questionnaire
from anamnesis.infrastructure.fuzzy.variables import LinguisticVariables, load_linguistic_variables
from anamnesis.infrastructure.knowledge.practice_selection import load_practice_selection
from anamnesis.infrastructure.llm.file_instructions import FileInstructions
from anamnesis.infrastructure.reasoning.ontology import OntologyNames, read_names
from anamnesis.infrastructure.reasoning.owl_reasoner import OwlCaseReasoner
from anamnesis.infrastructure.reasoning.owl_vocabulary import OwlOntologyVocabulary
from anamnesis.main.config.knowledge import KnowledgeConfig


class KnowledgeProvider(Provider):
    """Знания без языка: онтология, правила подбора, переменные, инструкции модели."""

    scope: BaseScope | None = Scope.APP

    assessment_service: CompositeDependencySource = provide(AssessmentService)

    @provide
    def questionnaire(self, config: KnowledgeConfig) -> Questionnaire:
        return Questionnaire(question_limit=config.question_limit)

    @provide
    def ontology_names(self, config: KnowledgeConfig) -> OntologyNames:
        return read_names(config.ontology_path)

    @provide
    def vocabulary(self, config: KnowledgeConfig) -> IOntologyVocabulary:
        return OwlOntologyVocabulary.load(config.ontology_path)

    @provide
    def reasoner(self, config: KnowledgeConfig) -> ICaseReasoner:
        return OwlCaseReasoner.load(
            config.ontology_path,
            max_concurrency=config.reasoner_concurrency,
        )

    @provide
    def practice_selection(self, config: KnowledgeConfig) -> PracticeSelection:
        return load_practice_selection(config.practice_selection_path)

    @provide
    def linguistic_variables(self, config: KnowledgeConfig) -> LinguisticVariables:
        return load_linguistic_variables(config.linguistic_variables_path)

    @provide
    def instructions(self, config: KnowledgeConfig) -> IInstructions:
        return FileInstructions.load(config.instructions_dir)
