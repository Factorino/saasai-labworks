from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter, status

from anamnesis.application.commands.chat.delete_chat import DeleteChat, DeleteChatRequest
from anamnesis.application.commands.chat.finish_chat import (
    FinishChat,
    FinishChatRequest,
    FinishChatResponse,
)
from anamnesis.application.commands.chat.post_message import (
    PostMessage,
    PostMessageBody,
    PostMessageRequest,
    PostMessageResponse,
)
from anamnesis.application.commands.chat.start_chat import (
    StartChat,
    StartChatRequest,
    StartChatResponse,
)
from anamnesis.application.queries.chat.get_summary import (
    GetSummary,
    GetSummaryRequest,
    GetSummaryResponse,
)
from anamnesis.domain.entities.chat import ChatId


router = APIRouter(prefix="/chats", tags=["Chats"], route_class=DishkaRoute)


@router.post("", status_code=status.HTTP_201_CREATED)
async def start_chat(
    request: StartChatRequest,
    interactor: FromDishka[StartChat],
) -> StartChatResponse:
    return await interactor.execute(request)


@router.post("/{chat_id}/messages")
async def post_message(
    chat_id: ChatId,
    body: PostMessageBody,
    interactor: FromDishka[PostMessage],
) -> PostMessageResponse:
    return await interactor.execute(PostMessageRequest(chat_id=chat_id, **body.model_dump()))


@router.post("/{chat_id}/finish")
async def finish_chat(
    chat_id: ChatId,
    interactor: FromDishka[FinishChat],
) -> FinishChatResponse:
    return await interactor.execute(FinishChatRequest(chat_id=chat_id))


@router.get("/{chat_id}/summary")
async def get_summary(
    chat_id: ChatId,
    interactor: FromDishka[GetSummary],
) -> GetSummaryResponse:
    return await interactor.execute(GetSummaryRequest(chat_id=chat_id))


@router.delete("/{chat_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chat(
    chat_id: ChatId,
    interactor: FromDishka[DeleteChat],
) -> None:
    await interactor.execute(DeleteChatRequest(chat_id=chat_id))
