from dishka import BaseScope, Provider, Scope, provide

from anamnesis.application.interfaces.safety.crisis_detector import ICrisisDetector
from anamnesis.application.interfaces.safety.reply_guard import IReplyGuard
from anamnesis.infrastructure.safety.combined_detector import CombinedCrisisDetector
from anamnesis.infrastructure.safety.encoder_detector import EncoderCrisisDetector
from anamnesis.infrastructure.safety.lexicon_detector import LexiconCrisisDetector
from anamnesis.infrastructure.safety.reply_guard import LexiconReplyGuard
from anamnesis.infrastructure.text.language import LanguageProfiles
from anamnesis.main.config.knowledge import KnowledgeConfig


class SafetyProvider(Provider):
    scope: BaseScope | None = Scope.APP

    @provide
    def detector(self, config: KnowledgeConfig, profiles: LanguageProfiles) -> ICrisisDetector:
        lexicon: LexiconCrisisDetector = LexiconCrisisDetector.load(
            config.resources_dir,
            profiles,
        )
        if not config.crisis_classifier:
            return lexicon

        encoder: EncoderCrisisDetector = EncoderCrisisDetector.load(
            config.resources_dir,
            config.languages,
            config.models_dir,
        )
        return CombinedCrisisDetector(lexicon, encoder)

    @provide
    def reply_guard(self, config: KnowledgeConfig, profiles: LanguageProfiles) -> IReplyGuard:
        return LexiconReplyGuard.load(config.resources_dir, profiles)
