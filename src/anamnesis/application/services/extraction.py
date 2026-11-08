from collections.abc import Iterable, Mapping
import logging
from typing import Any, Final

from anamnesis.application.dto.estimate import Estimate, LinguisticTerm
from anamnesis.application.dto.extraction import ExtractionReply, FoundConcept, reply_model
from anamnesis.application.errors.llm import (
    LanguageModelReplyError,
    LanguageModelUnavailableError,
)
from anamnesis.application.interfaces.common.clock import IClock
from anamnesis.application.interfaces.extraction.estimate_extractor import IEstimateExtractor
from anamnesis.application.interfaces.extraction.fact_extractor import IFactExtractor
from anamnesis.application.interfaces.extraction.fact_normalizer import IFactNormalizer
from anamnesis.application.interfaces.knowledge.vocabulary import IOntologyVocabulary, Vocabulary
from anamnesis.application.interfaces.llm.instructions import IInstructions, Instruction
from anamnesis.application.interfaces.llm.language_model import ILanguageModel, ModelRequest
from anamnesis.application.interfaces.localization.text_catalog import ITextCatalog
from anamnesis.application.services.model_data import data_message
from anamnesis.domain.enums.fact_kind import ESTIMATED_FACTS, FactKind
from anamnesis.domain.errors.common import ValidationError
from anamnesis.domain.types import LanguageCode, TermId
from anamnesis.domain.value_objects.case_facts import CaseFacts
from anamnesis.domain.value_objects.evidence import Evidence


_logger: Final[logging.Logger] = logging.getLogger(__name__)

_TEMPERATURE: Final[float] = 0.0
"""Извлечение должно быть воспроизводимым."""


class FactExtraction:
    """Гибридное извлечение сведений: словарь, затем языковая модель с подсказками.

    Словарь находит термины-кандидаты, модель получает реплику и кандидатов и
    отвечает по схеме, в которой допустимы только понятия онтологии и термы
    лингвистических переменных. Ответ модели проверяется ещё раз: чужие и
    зарезервированные понятия отбрасываются, цитата и цель сохраняются, только
    если они есть в реплике. Скрининг самоповреждения из текста не берётся, а
    влияние — только из ответа на вопрос о нём. Если
    модель недоступна или ответила неверно, остаётся результат словаря.
    """

    def __init__(
        self,
        *,
        lexicon: IFactExtractor,
        estimator: IEstimateExtractor,
        normalizer: IFactNormalizer,
        model: ILanguageModel,
        vocabulary: IOntologyVocabulary,
        instructions: IInstructions,
        catalog: ITextCatalog,
        clock: IClock,
    ) -> None:
        self._lexicon: IFactExtractor = lexicon
        self._estimator: IEstimateExtractor = estimator
        self._normalizer: IFactNormalizer = normalizer
        self._model: ILanguageModel = model
        self._vocabulary: Vocabulary = vocabulary.vocabulary()
        self._instructions: IInstructions = instructions
        self._catalog: ITextCatalog = catalog
        self._clock: IClock = clock
        self._manifestations: frozenset[TermId] = (
            self._vocabulary.manifestations - self._vocabulary.reserved
        )
        self._stressors: frozenset[TermId] = self._vocabulary.stressors - self._vocabulary.reserved
        self._reply_model: type[ExtractionReply] = reply_model(
            manifestations=self._manifestations,
            stressors=self._stressors,
            durations=normalizer.terms(FactKind.DURATION),
            frequencies=normalizer.terms(FactKind.FREQUENCY),
            impacts=normalizer.terms(FactKind.IMPACT),
        )
        self._system_texts: dict[LanguageCode, str] = {}

    async def extract(
        self,
        text: str,
        language: LanguageCode,
        question: FactKind | None = None,
        *,
        with_model: bool = True,
    ) -> CaseFacts:
        """Сведения из реплики.

        Args:
            text: Рассказ или свой ответ на вопрос.
            language: Язык реплики.
            question: На какой вопрос ответ; `None` — свободный рассказ. В ответе
                о длительности, частоте или влиянии число или выражение из
                словаря важнее терма модели, а если оно нашлось, модель не нужна.
            with_model: Звать ли модель; в кризисе работает только словарь.
        """
        found: CaseFacts = await self._lexicon.extract(text, language)
        estimated: CaseFacts | None = await self._estimate(text, language, question)
        if estimated is not None:
            return found.merge(estimated)
        if not with_model:
            return found
        reply: ExtractionReply | None = await self._ask_model(text, language, question, found)
        modelled: CaseFacts = (
            self._facts(reply, text, found, question) if reply is not None else CaseFacts()
        )
        return found.merge(modelled)

    async def _estimate(
        self,
        text: str,
        language: LanguageCode,
        question: FactKind | None,
    ) -> CaseFacts | None:
        """Оценка по словарю — только в ответе на вопрос об оцениваемом сведении."""
        if question not in ESTIMATED_FACTS:
            return None
        estimate: Estimate | None = await self._estimator.extract(text, question, language)
        return self._normalizer.normalize(estimate) if estimate is not None else None

    async def _ask_model(
        self,
        text: str,
        language: LanguageCode,
        question: FactKind | None,
        found: CaseFacts,
    ) -> ExtractionReply | None:
        """Ответ модели или `None`, если она недоступна или ответила неверно."""
        request = ModelRequest(
            instruction=self._system_text(language),
            messages=(data_message(self._data(text, question, found)),),
            temperature=_TEMPERATURE,
        )
        try:
            return await self._model.complete_structured(request, self._reply_model)
        except (LanguageModelUnavailableError, LanguageModelReplyError) as error:
            _logger.warning("Extraction falls back to the lexicon: %s", error)
            return None

    def _system_text(self, language: LanguageCode) -> str:
        """Инструкция и перечень понятий с названиями на языке реплики."""
        if language not in self._system_texts:
            sections: list[str] = [
                self._instructions.text(Instruction.EXTRACTION),
                "Manifestation concepts:\n" + self._concept_list(self._manifestations, language),
                "Stressor concepts:\n" + self._concept_list(self._stressors, language),
            ]
            self._system_texts[language] = "\n\n".join(sections)
        return self._system_texts[language]

    def _concept_list(self, terms: Iterable[TermId], language: LanguageCode) -> str:
        lines: list[str] = []
        for term in sorted(terms):
            description: str = self._catalog.description(term, language)
            name: str = self._catalog.term(term, language)
            lines.append(f"- {term}: {name}" + (f" — {description}" if description else ""))
        return "\n".join(lines)

    def _data(
        self,
        text: str,
        question: FactKind | None,
        found: CaseFacts,
    ) -> Mapping[str, Any]:
        """Реплика и кандидаты словаря как данные для модели."""
        candidates: list[dict[str, str]] = [
            {"concept": self._concept(evidence.term), "quote": evidence.quote}
            for evidence in (*found.manifestations, *found.stressors)
        ]
        return {
            "text": text,
            "question": question,
            "today": self._clock.now().date().isoformat(),
            "candidates": candidates,
        }

    def _facts(
        self,
        reply: ExtractionReply,
        text: str,
        found: CaseFacts,
        question: FactKind | None,
    ) -> CaseFacts:
        """Сведения из ответа модели после проверки; неверный ответ даёт пустые сведения.

        В ответе о длительности, частоте или влиянии «Другое» не берётся: это
        не жалоба. Цель показывается в сводке, поэтому берётся только дословная
        цитата: иначе текст модели попал бы туда без проверки. Влияние берётся
        только из ответа на вопрос о нём: тяжёлое влияние даёт L3 (R06), а L3
        после рассказа переводит чат в кризис, который не должен зависеть от
        догадки модели.
        """
        known: set[TermId] = {
            self._concept(evidence.term) for evidence in (*found.manifestations, *found.stressors)
        }
        try:
            facts = CaseFacts(
                manifestations=self._evidence(
                    reply.manifestations, self._manifestations, known, text
                ),
                stressors=self._evidence(reply.stressors, self._stressors, known, text),
                unrecognized=tuple(
                    quote
                    for quote in reply.other
                    if question not in ESTIMATED_FACTS and _contains(text, quote)
                ),
                goal=reply.goal if reply.goal and _contains(text, reply.goal) else None,
            )
            for fact, term in (
                (FactKind.DURATION, reply.duration),
                (FactKind.FREQUENCY, reply.frequency),
                (FactKind.IMPACT, reply.impact if question is FactKind.IMPACT else None),
            ):
                facts = facts.merge(self._term_facts(fact, term))
        except (ValidationError, ValueError) as error:
            _logger.warning("Extraction ignores an invalid model reply: %s", error)
            return CaseFacts()
        return facts

    @staticmethod
    def _evidence(
        items: Iterable[FoundConcept],
        allowed: frozenset[TermId],
        known: set[TermId],
        text: str,
    ) -> tuple[Evidence, ...]:
        """Допустимые понятия, которых ещё нет у словаря; цитата — только из реплики."""
        return tuple(
            Evidence(term=item.term, quote=item.quote if _contains(text, item.quote) else "")
            for item in items
            if item.term in allowed and item.term not in known
        )

    def _term_facts(self, fact: FactKind, term: LinguisticTerm | None) -> CaseFacts:
        if term is None:
            return CaseFacts()
        return self._normalizer.normalize(Estimate(fact=fact, terms={term: 1.0}))

    def _concept(self, term: TermId) -> TermId:
        return self._vocabulary.concepts.get(term, term)


def _contains(text: str, quote: str) -> bool:
    """Есть ли фрагмент в реплике, без учёта регистра и лишних пробелов."""
    needle: str = " ".join(quote.split()).casefold()
    return bool(needle) and needle in " ".join(text.split()).casefold()
