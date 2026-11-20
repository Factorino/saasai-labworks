from collections.abc import AsyncIterator

from dishka import AsyncContainer
import pytest

from anamnesis.main.config.config import Config
from anamnesis.main.config.knowledge import KnowledgeConfig
from anamnesis.main.di.container import create_container
from anamnesis.main.startup import prepare
from tests.integration.support.model import ScriptedModel, model_provider
from tests.integration.support.service import Service


@pytest.fixture(scope="session")
def scripted_model() -> ScriptedModel:
    return ScriptedModel()


@pytest.fixture
def model(scripted_model: ScriptedModel) -> ScriptedModel:
    scripted_model.reset()
    return scripted_model


@pytest.fixture(scope="session")
async def container(scripted_model: ScriptedModel) -> AsyncIterator[AsyncContainer]:
    config: Config = Config.model_construct(knowledge=KnowledgeConfig(crisis_classifier=False))
    async with create_container(config, model_provider(scripted_model)) as app:
        await prepare(app)
        yield app


@pytest.fixture
def service(container: AsyncContainer, model: ScriptedModel) -> Service:
    return Service(container)
