from typing import TYPE_CHECKING, override

from anamnesis.application.dto.base import DTO
from anamnesis.application.dto.views.summary import SummaryView
from anamnesis.application.interfaces.common.interactor import Interactor
from anamnesis.application.interfaces.reasoning.case_reasoner import ICaseReasoner
from anamnesis.application.services.languages import SupportedLanguages
from anamnesis.application.services.rendering import ViewRenderer
from anamnesis.domain.enums.crisis import SelfHarmScreening
from anamnesis.domain.enums.scales import Frequency, ImpactDegree
from anamnesis.domain.services.assessment import AssessmentService
from anamnesis.domain.types import LanguageCode, TermId
from anamnesis.domain.value_objects.case_facts import CaseFacts
from anamnesis.domain.value_objects.duration import Duration
from anamnesis.domain.value_objects.evidence import Evidence


if TYPE_CHECKING:
    from anamnesis.domain.value_objects.assessment import Assessment
    from anamnesis.domain.value_objects.inference import InferenceResult


class AssessCaseRequest(DTO):
    """Сведения о случае без диалога: для проверки правил и демонстрации.

    Attributes:
        language: Язык сводки.
        manifestations: Проявления.
        stressors: Стрессоры.
        duration_weeks: Длительность в неделях.
        frequency: Частота.
        impact: Влияние на жизнь.
        affected_domains: Затронутые сферы.
        self_harm: Скрининг самоповреждения.
    """

    language: LanguageCode

    manifestations: tuple[TermId, ...] = ()
    stressors: tuple[TermId, ...] = ()

    duration_weeks: int | None = None
    frequency: Frequency | None = None
    impact: ImpactDegree | None = None
    affected_domains: frozenset[TermId] = frozenset()

    self_harm: SelfHarmScreening | None = None


class AssessCaseResponse(DTO):
    """Оценка случая.

    Attributes:
        summary: Сводка по шаблонам, без текста модели.
    """

    summary: SummaryView


class AssessCase(Interactor[AssessCaseRequest, AssessCaseResponse]):
    """Оценивает случай по готовым сведениям, минуя диалог."""

    def __init__(
        self,
        *,
        reasoner: ICaseReasoner,
        assessment_service: AssessmentService,
        languages: SupportedLanguages,
        renderer: ViewRenderer,
    ) -> None:
        self._reasoner: ICaseReasoner = reasoner
        self._assessment_service: AssessmentService = assessment_service
        self._languages: SupportedLanguages = languages
        self._renderer: ViewRenderer = renderer

    @staticmethod
    def _facts(request: AssessCaseRequest) -> CaseFacts:
        """Сведения о случае из запроса."""
        duration: Duration | None = (
            Duration(weeks=request.duration_weeks) if request.duration_weeks is not None else None
        )

        facts: CaseFacts = CaseFacts(
            manifestations=tuple(Evidence(term=term) for term in request.manifestations),
            stressors=tuple(Evidence(term=term) for term in request.stressors),
            duration=duration,
            frequency=request.frequency,
            impact=request.impact,
            affected_domains=request.affected_domains,
            self_harm=request.self_harm,
        )
        return facts

    @override
    async def execute(self, request: AssessCaseRequest) -> AssessCaseResponse:
        self._languages.validate(request.language)

        facts: CaseFacts = self._facts(request)
        inference: InferenceResult = await self._reasoner.infer(facts)
        crisis: bool = facts.self_harm is not None and facts.self_harm.is_crisis
        assessment: Assessment = self._assessment_service.assess(facts, inference, crisis=crisis)

        summary: SummaryView = self._renderer.summary(request.language, assessment, facts)
        return AssessCaseResponse(summary=summary)
