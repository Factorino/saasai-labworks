from pydantic import Field

from anamnesis.main.config.base import BaseConfig


class ServerConfig(BaseConfig):
    host: str = "127.0.0.1"
    port: int = Field(default=8000, ge=1, le=65535)
    reload: bool = False
