from anamnesis.application.dto.views.chat import ChatView
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
from anamnesis.application.interfaces.localization.text_catalog import ITextCatalog
from anamnesis.domain.entities.chat import Chat
from anamnesis.domain.enums.crisis_category import CrisisCategory
from anamnesis.domain.enums.referral import Referral
from anamnesis.domain.enums.urgency_level import UrgencyLevel
from anamnesis.domain.types import LanguageCode, TermId
from anamnesis.domain.value_objects.assessment import Assessment
from anamnesis.domain.value_objects.case_facts import CaseFacts
from anamnesis.domain.value_objects.evidence import Evidence
from anamnesis.domain.value_objects.inference import PracticeAdvice
from anamnesis.domain.value_objects.narrative import Narrative
from anamnesis.domain.value_objects.question import Answer, Question


class ViewRenderer:
    """Собирает представления из доменных объектов с текстами на языке чата."""

    def __init__(self, catalog: ITextCatalog) -> None:
        self._catalog: ITextCatalog = catalog

    @staticmethod
    def chat(chat: Chat) -> ChatView:
        return ChatView(
            id=chat.id,
            language=chat.language,
            stage=chat.stage,
            created_at=chat.created_at,
        )

    def question(self, question: Question, language: LanguageCode) -> QuestionView:
        return QuestionView(
            fact=question.fact,
            text=self._catalog.question(question, language),
            options=tuple(
                OptionView(code=code, label=self._catalog.option(question.fact, code, language))
                for code in question.options
            ),
            multiple=question.multiple,
            free_text=question.free_text,
        )

    def answer(self, question: Question, answer: Answer, language: LanguageCode) -> str:
        """Ответ для истории: свой текст или подписи выбранных вариантов."""
        if answer.text is not None:
            return answer.text
        return ", ".join(
            self._catalog.option(question.fact, code, language) for code in answer.option_codes
        )

    def summary(
        self,
        assessment: Assessment,
        facts: CaseFacts,
        language: LanguageCode,
        narrative: Narrative | None = None,
    ) -> SummaryView:
        """Сводка; без готового текста описание и запрос берутся из шаблонов."""
        return SummaryView(
            level=assessment.level,
            phrase=self._phrase(assessment, language),
            description=(
                narrative.description
                if narrative is not None
                else self._catalog.fallback_description(language)
            ),
            specialist_request=(
                narrative.request
                if narrative is not None
                else self._catalog.fallback_request(language)
            ),
            specialist=self._catalog.specialist(assessment.level, language),
            crisis=assessment.crisis,
            referrals=tuple(
                ReferralView(referral=referral, text=self._catalog.referral(referral, language))
                for referral in assessment.referrals
            ),
            helplines=self._helplines(assessment, language),
            signals=tuple(
                SignalView(category=signal.category, quote=signal.quote)
                for signal in assessment.signals
            ),
            support_others=self._support_others(assessment, language),
            practices=tuple(
                view
                for advice in assessment.advised_practices
                if (view := self._practice(advice, language)) is not None
            ),
            clusters=tuple(self._term(term, language) for term in assessment.clusters),
            explanation=tuple(
                RuleView(rule=rule, explanation=self._catalog.rule(rule, language))
                for rule in assessment.fired_rules
            ),
            missing=tuple(sorted(assessment.missing)),
            approximations=self._approximations(facts, language),
            case=self._case(facts, language),
            disclaimer=self._catalog.disclaimer(language),
        )

    def _approximations(
        self,
        facts: CaseFacts,
        language: LanguageCode,
    ) -> tuple[ApproximationView, ...]:
        """Сведения, оценённые по размытым словам, с уверенностью."""
        return tuple(
            ApproximationView(
                fact=fact,
                confidence=confidence,
                text=self._catalog.approximate(fact, language),
            )
            for fact, confidence in sorted(facts.confidence.items())
        )

    def _helplines(
        self,
        assessment: Assessment,
        language: LanguageCode,
    ) -> tuple[HelplineView, ...]:
        """Контакты помощи — при любом срочном направлении."""
        urgent: set[Referral] = {Referral.CRISIS_HELPLINE, Referral.EMERGENCY_MEDICAL_CARE}
        if urgent.isdisjoint(assessment.referrals):
            return ()
        return self._catalog.helplines(language)

    def _support_others(self, assessment: Assessment, language: LanguageCode) -> str | None:
        """Совет поддержать близкого, если пользователь тревожится за другого человека."""
        categories: set[CrisisCategory] = {signal.category for signal in assessment.signals}
        if CrisisCategory.OTHER_PERSON not in categories:
            return None
        return self._catalog.support_others(language)

    def _phrase(self, assessment: Assessment, language: LanguageCode) -> str | None:
        """Формулировка уровня; L0 о самопомощи не показывается, если она запрещена."""
        if assessment.level is UrgencyLevel.L0 and not assessment.self_help:
            return None
        return self._catalog.level(assessment.level, language)

    def _case(self, facts: CaseFacts, language: LanguageCode) -> CaseView:
        return CaseView(
            manifestations=tuple(self._evidence(item, language) for item in facts.manifestations),
            stressors=tuple(self._evidence(item, language) for item in facts.stressors),
            unrecognized=facts.unrecognized,
            duration_weeks=facts.duration.weeks if facts.duration is not None else None,
            frequency=facts.frequency,
            impact=facts.impact,
            affected_domains=tuple(
                self._term(term, language) for term in sorted(facts.affected_domains)
            ),
            self_harm=facts.self_harm,
            sleep=facts.sleep,
            appetite=facts.appetite,
            energy=facts.energy,
            substance_use=facts.substance_use,
            goal=facts.goal,
            refused=tuple(sorted(facts.refused)),
        )

    def _practice(self, advice: PracticeAdvice, language: LanguageCode) -> PracticeView | None:
        """Практика с документом; без проверенного документа она не советуется."""
        guide: PracticeGuideView | None = self._catalog.practice_guide(advice.practice, language)
        if guide is None:
            return None
        return PracticeView(
            term=advice.practice,
            name=self._catalog.term(advice.practice, language),
            description=self._catalog.description(advice.practice, language),
            guide=guide,
            cautions=tuple(self._term(term, language) for term in sorted(advice.cautions)),
        )

    def _evidence(self, evidence: Evidence, language: LanguageCode) -> EvidenceView:
        return EvidenceView(
            term=evidence.term,
            name=self._catalog.term(evidence.term, language),
            quote=evidence.quote,
        )

    def _term(self, term: TermId, language: LanguageCode) -> TermView:
        return TermView(term=term, name=self._catalog.term(term, language))
