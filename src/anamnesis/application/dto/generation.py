from pydantic import Field

from anamnesis.application.dto.base import DTO


class NarrativeReply(DTO):
    description: str = Field(
        min_length=1,
        description="The person's state in plain, warm words, three to five sentences",
    )
    request: str = Field(
        min_length=1,
        description="What the person can say to a specialist, in the first person",
    )


class AnswerReply(DTO):
    text: str = Field(min_length=1, description="The answer to the person's message")
