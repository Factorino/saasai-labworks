from fastapi import APIRouter

from anamnesis.presentation.api.routes.assessments import router as assessments_router
from anamnesis.presentation.api.routes.chats import router as chats_router
from anamnesis.presentation.api.routes.health import router as health_router


__all__: list[str] = ["router"]


router = APIRouter()
router.include_router(health_router)
router.include_router(chats_router)
router.include_router(assessments_router)
