from anamnesis.application.dto.views.question import OptionView, QuestionView
from anamnesis.application.dto.views.summary import (
    ApproximationView,
    CaseView,
    EvidenceView,
    HelplineView,
    PracticeGuideView,
    PracticeView,
    ReferralView,
    RuleView,
    SignalView,
    SummaryView,
    TermView,
)
from anamnesis.application.interfaces.knowledge.knowledge_base import (
    IKnowledgeBase,
    PracticeGuide,
)
from anamnesis.application.interfaces.localization.concept_texts import IConceptTexts
from anamnesis.application.interfaces.localization.dialogue_texts import IDialogueTexts
from anamnesis.application.interfaces.localization.summary_texts import ISummaryTexts
from anamnesis.domain.enums.crisis import CrisisCategory
from anamnesis.domain.enums.recommendation import Referral, UrgencyLevel
from anamnesis.domain.services.practice_selection import PracticeSelection
from anamnesis.domain.types import LanguageCode, TermId
from anamnesis.domain.value_objects.assessment import Assessment
from anamnesis.domain.value_objects.case_facts import CaseFacts
from anamnesis.domain.value_objects.clarification import Answer, Question
from anamnesis.domain.value_objects.evidence import Evidence
from anamnesis.domain.value_objects.narrative import Narrative
from anamnesis.domain.value_objects.practice import PracticeAdvice


class ViewRenderer:
    """Собирает представления для клиента из объектов домена с текстами на языке чата."""

    def __init__(
        self,
        *,
        dialogue_texts: IDialogueTexts,
        summary_texts: ISummaryTexts,
        concept_texts: IConceptTexts,
        knowledge: IKnowledgeBase,
        selection: PracticeSelection,
    ) -> None:
        self._dialogue_texts: IDialogueTexts = dialogue_texts
        self._summary_texts: ISummaryTexts = summary_texts
        self._concept_texts: IConceptTexts = concept_texts
        self._knowledge: IKnowledgeBase = knowledge
        self._selection: PracticeSelection = selection

    def question(self, language: LanguageCode, question: Question) -> QuestionView:
        """Вопрос с вариантами ответа."""
        options: tuple[OptionView, ...] = tuple(
            OptionView(
                code=code,
                label=self._dialogue_texts.option(language, question.fact, code),
            )
            for code in question.options
        )

        view: QuestionView = QuestionView(
            fact=question.fact,
            text=self._dialogue_texts.question(language, question),
            options=options,
            multiple=question.multiple,
            free_text=question.free_text,
        )
        return view

    def answer(self, language: LanguageCode, question: Question, answer: Answer) -> str:
        """Ответ для истории: свой текст или подписи выбранных вариантов."""
        if answer.text is not None:
            return answer.text

        labels: str = ", ".join(
            self._dialogue_texts.option(language, question.fact, code)
            for code in answer.option_codes
        )
        return labels

    def summary(
        self,
        language: LanguageCode,
        assessment: Assessment,
        facts: CaseFacts,
        narrative: Narrative | None = None,
    ) -> SummaryView:
        """Сводка; без готового текста описание и запрос берутся из шаблонов."""
        texts: ISummaryTexts = self._summary_texts
        description: str = (
            narrative.description
            if narrative is not None
            else texts.fallback_description(language)
        )
        request: str = (
            narrative.request if narrative is not None else texts.fallback_request(language)
        )

        summary: SummaryView = SummaryView(
            level=assessment.level,
            phrase=self._phrase(language, assessment),
            description=description,
            specialist_request=request,
            specialist=texts.specialist(language, assessment.level),
            crisis=assessment.crisis,
            referrals=tuple(
                ReferralView(referral=referral, text=texts.referral(language, referral))
                for referral in assessment.referrals
            ),
            helplines=self._helplines(language, assessment),
            signals=tuple(SignalView.from_domain(signal) for signal in assessment.signals),
            support_others=self._support_others(language, assessment),
            practices=self._practices(language, assessment),
            clusters=tuple(self._term(language, term) for term in assessment.clusters),
            explanation=tuple(
                RuleView(rule=rule, explanation=texts.rule(language, rule))
                for rule in assessment.fired_rules
            ),
            missing=tuple(sorted(assessment.missing)),
            approximations=self._approximations(language, facts),
            case=self._case(language, facts),
            disclaimer=texts.disclaimer(language),
        )
        return summary

    def _phrase(self, language: LanguageCode, assessment: Assessment) -> str | None:
        """Формулировка уровня; L0 о самопомощи не показывается, если она запрещена."""
        if assessment.level is UrgencyLevel.L0 and not assessment.self_help:
            return None
        return self._summary_texts.level(language, assessment.level)

    def _helplines(
        self,
        language: LanguageCode,
        assessment: Assessment,
    ) -> tuple[HelplineView, ...]:
        """Контакты помощи — при любом срочном направлении."""
        urgent: set[Referral] = {Referral.CRISIS_HELPLINE, Referral.EMERGENCY_MEDICAL_CARE}
        if urgent.isdisjoint(assessment.referrals):
            return ()

        helplines: tuple[HelplineView, ...] = tuple(
            HelplineView.from_helpline(helpline)
            for helpline in self._knowledge.helplines(language)
        )
        return helplines

    def _support_others(self, language: LanguageCode, assessment: Assessment) -> str | None:
        """Совет поддержать близкого, если пользователь тревожится за другого человека."""
        categories: set[CrisisCategory] = {signal.category for signal in assessment.signals}
        if CrisisCategory.OTHER_PERSON not in categories:
            return None
        return self._summary_texts.support_others(language)

    def _practices(
        self,
        language: LanguageCode,
        assessment: Assessment,
    ) -> tuple[PracticeView, ...]:
        """Практики для сводки; без проверенного документа практика не советуется."""
        guides: dict[TermId, PracticeGuide] = {
            advice.practice: guide
            for advice in assessment.advised_practices
            if (guide := self._knowledge.practice_guide(language, advice.practice)) is not None
        }

        selected: tuple[PracticeAdvice, ...] = self._selection.select(
            (advice for advice in assessment.advised_practices if advice.practice in guides),
            level=assessment.level,
            clusters=assessment.clusters,
        )

        practices: tuple[PracticeView, ...] = tuple(
            self._practice(language, advice, guides[advice.practice]) for advice in selected
        )
        return practices

    def _practice(
        self,
        language: LanguageCode,
        advice: PracticeAdvice,
        guide: PracticeGuide,
    ) -> PracticeView:
        view: PracticeView = PracticeView(
            term=advice.practice,
            name=self._concept_texts.name(language, advice.practice),
            description=self._concept_texts.description(language, advice.practice),
            guide=PracticeGuideView.from_guide(guide),
            cautions=tuple(self._term(language, term) for term in sorted(advice.cautions)),
        )
        return view

    def _approximations(
        self,
        language: LanguageCode,
        facts: CaseFacts,
    ) -> tuple[ApproximationView, ...]:
        """Сведения, оценённые по размытым словам, с уверенностью."""
        approximations: tuple[ApproximationView, ...] = tuple(
            ApproximationView(
                fact=fact,
                confidence=confidence,
                text=self._summary_texts.approximate(language, fact),
            )
            for fact, confidence in sorted(facts.confidence.items())
        )
        return approximations

    def _case(self, language: LanguageCode, facts: CaseFacts) -> CaseView:
        view: CaseView = CaseView(
            manifestations=tuple(self._evidence(language, item) for item in facts.manifestations),
            stressors=tuple(self._evidence(language, item) for item in facts.stressors),
            unrecognized=facts.unrecognized,
            duration_weeks=facts.duration.weeks if facts.duration is not None else None,
            frequency=facts.frequency,
            impact=facts.impact,
            affected_domains=tuple(
                self._term(language, term) for term in sorted(facts.affected_domains)
            ),
            self_harm=facts.self_harm,
            sleep=facts.sleep,
            appetite=facts.appetite,
            energy=facts.energy,
            substance_use=facts.substance_use,
            goal=facts.goal,
            refused=tuple(sorted(facts.refused)),
        )
        return view

    def _evidence(self, language: LanguageCode, evidence: Evidence) -> EvidenceView:
        return EvidenceView(
            term=evidence.term,
            name=self._concept_texts.name(language, evidence.term),
            quote=evidence.quote,
        )

    def _term(self, language: LanguageCode, term: TermId) -> TermView:
        return TermView(term=term, name=self._concept_texts.name(language, term))
