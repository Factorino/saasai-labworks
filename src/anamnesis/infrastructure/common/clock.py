from datetime import UTC, datetime
from typing import override

from anamnesis.application.interfaces.common.clock import IClock


class SystemClock(IClock):
    @override
    def now(self) -> datetime:
        return datetime.now(UTC)
