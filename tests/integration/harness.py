"""Сценарии чата для тестов: настоящие адаптеры, языковая модель — заглушка."""

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import cast, override

from anamnesis.application.commands.chat.finish_chat import FinishChat
from anamnesis.application.commands.chat.post_message import PostMessage, PostMessageRequest
from anamnesis.application.commands.chat.start_chat import StartChat
from anamnesis.application.dto.base import DTO
from anamnesis.application.dto.views.reply import ReplyView
from anamnesis.application.errors.llm import LanguageModelUnavailableError
from anamnesis.application.interfaces.llm.language_model import ILanguageModel, ModelRequest
from anamnesis.application.services.dialogue import DialogueService
from anamnesis.application.services.extraction import FactExtraction
from anamnesis.application.services.generation import TextGeneration
from anamnesis.application.services.rendering import ViewRenderer
from anamnesis.domain.entities.chat import ChatId
from anamnesis.domain.services.assessment import AssessmentService
from anamnesis.domain.services.questionnaire import Questionnaire
from anamnesis.domain.types import LanguageCode
from anamnesis.infrastructure.common.clock import SystemClock
from anamnesis.infrastructure.common.id_generator import ChatIdGenerator
from anamnesis.infrastructure.extraction.lexicon_estimator import LexiconEstimateExtractor
from anamnesis.infrastructure.extraction.lexicon_extractor import LexiconFactExtractor
from anamnesis.infrastructure.fuzzy.normalizer import FuzzyFactNormalizer
from anamnesis.infrastructure.fuzzy.variables import load_linguistic_variables
from anamnesis.infrastructure.llm.file_instructions import FileInstructions
from anamnesis.infrastructure.localization.locale import load_locales
from anamnesis.infrastructure.localization.text_catalog import YamlTextCatalog
from anamnesis.infrastructure.persistence.chat_repository import InMemoryChatRepository
from anamnesis.infrastructure.reasoning.owl_reasoner import OwlCaseReasoner
from anamnesis.infrastructure.reasoning.owl_vocabulary import OwlOntologyVocabulary
from anamnesis.infrastructure.safety.lexicon_detector import LexiconCrisisDetector
from anamnesis.infrastructure.safety.reply_guard import LexiconReplyGuard


ROOT = Path(__file__).parents[2]
RU = LanguageCode("ru")
LOCALES = load_locales(ROOT / "locales")
CATALOG = YamlTextCatalog(LOCALES)
INSTRUCTIONS = FileInstructions(ROOT / "knowledge" / "instructions")
VARIABLES = load_linguistic_variables(ROOT / "knowledge" / "linguistic_variables.yaml")


class ScriptedModel(ILanguageModel):
    """Отдаёт заготовленные ответы подходящего типа и запоминает запросы.

    Если подходящего ответа нет, модель считается недоступной.
    """

    def __init__(self, *replies: DTO) -> None:
        self._replies: list[DTO] = list(replies)
        self.requests: list[ModelRequest] = []

    @override
    async def complete_structured[OutputT: DTO](
        self,
        request: ModelRequest,
        output: type[OutputT],
    ) -> OutputT:
        for reply in self._replies:
            if issubclass(output, type(reply)):
                self._replies.remove(reply)
                self.requests.append(request)
                return cast("OutputT", reply)
        raise LanguageModelUnavailableError(model="scripted", reason="no scripted reply")


@dataclass(frozen=True)
class Service:
    start: StartChat
    post: PostMessage
    finish: FinishChat
    extraction: FactExtraction


def build_service(model: ILanguageModel) -> Service:
    renderer = ViewRenderer(CATALOG)
    repository = InMemoryChatRepository()
    ontology = ROOT / "ontology" / "anamnesis.owl"
    extraction = FactExtraction(
        lexicon=LexiconFactExtractor(LOCALES),
        estimator=LexiconEstimateExtractor(LOCALES, VARIABLES),
        normalizer=FuzzyFactNormalizer(VARIABLES),
        model=model,
        vocabulary=OwlOntologyVocabulary(ontology_path=ontology),
        instructions=INSTRUCTIONS,
        catalog=CATALOG,
        clock=SystemClock(),
    )
    dialogue = DialogueService(
        questionnaire=Questionnaire(),
        assessment_service=AssessmentService(),
        reasoner=OwlCaseReasoner(ontology_path=ontology),
        catalog=CATALOG,
        renderer=renderer,
        generation=TextGeneration(
            model=model,
            guard=LexiconReplyGuard(LOCALES),
            instructions=INSTRUCTIONS,
        ),
    )
    return Service(
        start=StartChat(
            chat_repository=repository,
            catalog=CATALOG,
            renderer=renderer,
            id_generator=ChatIdGenerator(),
            clock=SystemClock(),
        ),
        post=PostMessage(
            chat_repository=repository,
            extraction=extraction,
            detector=LexiconCrisisDetector(LOCALES),
            dialogue=dialogue,
            renderer=renderer,
        ),
        finish=FinishChat(chat_repository=repository, dialogue=dialogue),
        extraction=extraction,
    )


async def post(
    service: Service,
    chat_id: ChatId,
    text: str = "",
    options: Sequence[str] = (),
) -> ReplyView:
    request = PostMessageRequest.model_validate(
        {"chat_id": chat_id, "text": text, "option_codes": options},
    )
    return (await service.post.execute(request)).reply
