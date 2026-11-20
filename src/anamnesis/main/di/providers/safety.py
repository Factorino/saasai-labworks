from dishka import BaseScope, Provider, Scope, provide

from anamnesis.application.interfaces.safety.crisis_detector import ICrisisDetector
from anamnesis.application.interfaces.safety.reply_guard import IReplyGuard
from anamnesis.infrastructure.safety.lexicon_detector import LexiconCrisisDetector
from anamnesis.infrastructure.safety.reply_guard import LexiconReplyGuard
from anamnesis.infrastructure.text.language import LanguageProfiles
from anamnesis.main.config.knowledge import KnowledgeConfig


class SafetyProvider(Provider):
    scope: BaseScope | None = Scope.APP

    @provide
    def detector(self, config: KnowledgeConfig, profiles: LanguageProfiles) -> ICrisisDetector:
        return LexiconCrisisDetector.load(config.resources_dir, profiles)

    @provide
    def reply_guard(self, config: KnowledgeConfig, profiles: LanguageProfiles) -> IReplyGuard:
        return LexiconReplyGuard.load(config.resources_dir, profiles)
