from typing import Final

import uvicorn

from anamnesis.main.config.config import Config


_APP_FACTORY: Final[str] = "anamnesis.main.api.app:app_factory"


def main() -> None:
    config: Config = Config.load()
    uvicorn.run(
        _APP_FACTORY,
        factory=True,
        host=config.server.host,
        port=config.server.port,
        reload=config.server.reload,
    )
