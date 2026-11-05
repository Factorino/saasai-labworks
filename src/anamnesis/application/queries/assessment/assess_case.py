from typing import TYPE_CHECKING, override

from anamnesis.application.dto.base import DTO
from anamnesis.application.dto.views.summary import SummaryView
from anamnesis.application.errors.knowledge import UnsupportedLanguageError
from anamnesis.application.interfaces.common.interactor import Interactor
from anamnesis.application.interfaces.localization.text_catalog import ITextCatalog
from anamnesis.application.interfaces.reasoning.case_reasoner import ICaseReasoner
from anamnesis.application.services.rendering import ViewRenderer
from anamnesis.domain.enums.frequency import Frequency
from anamnesis.domain.enums.impact_degree import ImpactDegree
from anamnesis.domain.enums.self_harm_screening import SelfHarmScreening
from anamnesis.domain.services.assessment import AssessmentService
from anamnesis.domain.types import LanguageCode, TermId
from anamnesis.domain.value_objects.case_facts import CaseFacts
from anamnesis.domain.value_objects.duration import Duration
from anamnesis.domain.value_objects.evidence import Evidence


if TYPE_CHECKING:
    from anamnesis.domain.value_objects.assessment import Assessment
    from anamnesis.domain.value_objects.inference import InferenceResult


class AssessCaseRequest(DTO):
    language: LanguageCode
    manifestations: tuple[TermId, ...] = ()
    stressors: tuple[TermId, ...] = ()
    duration_weeks: int | None = None
    frequency: Frequency | None = None
    impact: ImpactDegree | None = None
    affected_domains: frozenset[TermId] = frozenset()
    self_harm: SelfHarmScreening | None = None


class AssessCaseResponse(DTO):
    summary: SummaryView


class AssessCase(Interactor[AssessCaseRequest, AssessCaseResponse]):
    def __init__(
        self,
        *,
        reasoner: ICaseReasoner,
        assessment_service: AssessmentService,
        catalog: ITextCatalog,
        renderer: ViewRenderer,
    ) -> None:
        self._reasoner: ICaseReasoner = reasoner
        self._assessment_service: AssessmentService = assessment_service
        self._catalog: ITextCatalog = catalog
        self._renderer: ViewRenderer = renderer

    @override
    async def execute(self, request: AssessCaseRequest) -> AssessCaseResponse:
        self._validate_language(request.language)
        facts: CaseFacts = self._facts(request)
        inference: InferenceResult = await self._reasoner.infer(facts)
        crisis: bool = facts.self_harm is not None and facts.self_harm.is_crisis
        assessment: Assessment = self._assessment_service.assess(facts, inference, crisis=crisis)
        return AssessCaseResponse(
            summary=self._renderer.summary(assessment, facts, request.language),
        )

    @staticmethod
    def _facts(request: AssessCaseRequest) -> CaseFacts:
        return CaseFacts(
            manifestations=tuple(Evidence(term=term) for term in request.manifestations),
            stressors=tuple(Evidence(term=term) for term in request.stressors),
            duration=(
                Duration(weeks=request.duration_weeks)
                if request.duration_weeks is not None
                else None
            ),
            frequency=request.frequency,
            impact=request.impact,
            affected_domains=request.affected_domains,
            self_harm=request.self_harm,
        )

    def _validate_language(self, language: LanguageCode) -> None:
        if not self._catalog.supports(language):
            raise UnsupportedLanguageError(language=language)
