import asyncio
from typing import override

from anamnesis.application.interfaces.safety.crisis_detector import ICrisisDetector
from anamnesis.domain.types import LanguageCode
from anamnesis.domain.value_objects.crisis_signal import CrisisSignal


class CombinedCrisisDetector(ICrisisDetector):
    """Фасад детекторов: кризис есть, если его нашёл хотя бы один."""

    def __init__(self, *detectors: ICrisisDetector) -> None:
        self._detectors: tuple[ICrisisDetector, ...] = detectors

    @override
    async def detect(self, text: str, language: LanguageCode) -> tuple[CrisisSignal, ...]:
        results: list[tuple[CrisisSignal, ...]] = await asyncio.gather(
            *(detector.detect(text, language) for detector in self._detectors),
        )

        signals: tuple[CrisisSignal, ...] = tuple(
            dict.fromkeys(signal for signals in results for signal in signals),
        )
        return signals
