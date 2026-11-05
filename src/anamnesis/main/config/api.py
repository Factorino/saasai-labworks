from pydantic import Field

from anamnesis.main.config.base import BaseConfig


class CORSConfig(BaseConfig):
    allow_origins: tuple[str, ...] = ("*",)
    allow_methods: tuple[str, ...] = ("*",)
    allow_headers: tuple[str, ...] = ("*",)
    max_age: int = Field(default=600, ge=0)


class APIConfig(BaseConfig):
    docs_enabled: bool = True
    cors: CORSConfig = Field(default_factory=CORSConfig)

    @property
    def docs_url(self) -> str | None:
        return "/docs" if self.docs_enabled else None

    @property
    def redoc_url(self) -> str | None:
        return "/redoc" if self.docs_enabled else None

    @property
    def openapi_url(self) -> str | None:
        return "/openapi.json" if self.docs_enabled else None
