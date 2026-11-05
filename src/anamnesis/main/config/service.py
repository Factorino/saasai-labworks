from anamnesis.main.config.base import BaseConfig


class ServiceConfig(BaseConfig):
    title: str = "Anamnesis"
    version: str = "0.1.0"
    debug: bool = False
