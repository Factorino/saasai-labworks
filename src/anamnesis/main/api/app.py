from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from anamnesis.domain.errors.base import AppError
from anamnesis.main.config.config import Config
from anamnesis.main.di.container import create_container
from anamnesis.presentation.api.handlers.error import error_handler
from anamnesis.presentation.api.routes import router


if TYPE_CHECKING:
    from dishka import AsyncContainer


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncGenerator[None]:
    container: AsyncContainer = app.state.dishka_container
    try:
        yield
    finally:
        await container.close()


def app_factory() -> FastAPI:
    return create_app(Config.load())


def create_app(config: Config) -> FastAPI:
    app = FastAPI(
        title=config.service.title,
        version=config.service.version,
        debug=config.service.debug,
        docs_url=config.api.docs_url,
        redoc_url=config.api.redoc_url,
        openapi_url=config.api.openapi_url,
        lifespan=_lifespan,
    )

    container: AsyncContainer = create_container(config)
    setup_dishka(container, app)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.api.cors.allow_origins,
        allow_methods=config.api.cors.allow_methods,
        allow_headers=config.api.cors.allow_headers,
        max_age=config.api.cors.max_age,
    )

    app.include_router(router)
    app.add_exception_handler(AppError, error_handler)
    return app
