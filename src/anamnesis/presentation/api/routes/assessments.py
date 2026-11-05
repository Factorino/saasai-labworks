from dishka.integrations.fastapi import DishkaRoute, FromDishka
from fastapi import APIRouter

from anamnesis.application.queries.assessment.assess_case import (
    AssessCase,
    AssessCaseRequest,
    AssessCaseResponse,
)


router = APIRouter(prefix="/assessments", tags=["Assessments"], route_class=DishkaRoute)


@router.post("")
async def assess_case(
    request: AssessCaseRequest,
    interactor: FromDishka[AssessCase],
) -> AssessCaseResponse:
    return await interactor.execute(request)
