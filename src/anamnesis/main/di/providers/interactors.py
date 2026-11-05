from dishka import BaseScope, Provider, Scope, provide_all
from dishka.dependency_source import CompositeDependencySource

from anamnesis.application.commands.chat.delete_chat import DeleteChat
from anamnesis.application.commands.chat.finish_chat import FinishChat
from anamnesis.application.commands.chat.post_message import PostMessage
from anamnesis.application.commands.chat.start_chat import StartChat
from anamnesis.application.queries.assessment.assess_case import AssessCase
from anamnesis.application.queries.chat.get_summary import GetSummary


class InteractorsProvider(Provider):
    scope: BaseScope | None = Scope.REQUEST

    interactors: CompositeDependencySource = provide_all(
        StartChat,
        PostMessage,
        FinishChat,
        DeleteChat,
        GetSummary,
        AssessCase,
    )
