import asyncio
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
import re
from types import MappingProxyType
from typing import Final, override

import numpy as np
from pydantic import Field

from anamnesis.application.interfaces.safety.crisis_detector import ICrisisDetector
from anamnesis.domain.enums.crisis import CrisisCategory
from anamnesis.domain.types import LanguageCode
from anamnesis.domain.value_objects.crisis_signal import CrisisSignal
from anamnesis.infrastructure.filesystem.yaml_reader import YamlFile, read_yaml
from anamnesis.infrastructure.safety.sentence_encoder import SentenceEncoder, Vectors


_CLASSIFIER_FILE: Final[str] = "crisis_classifier.yaml"

_SENTENCE_END: Final[re.Pattern[str]] = re.compile(r"[.!?\n]+")
"""Граница предложения в реплике."""


class ClassifierFile(YamlFile):
    """`resources/<язык>/crisis_classifier.yaml`: обученная часть классификатора.

    Attributes:
        encoder: Каталог энкодера в `models/`, на векторах которого обучен классификатор.
        threshold: С какой вероятности реплика считается кризисной.
        intercept: Свободный член логистической регрессии.
        weights: Веса логистической регрессии по компонентам вектора.
    """

    encoder: str
    threshold: float = Field(gt=0, lt=1)
    intercept: float
    weights: tuple[float, ...] = Field(min_length=1)


@dataclass(frozen=True, slots=True)
class _Classifier:
    """Классификатор одного языка: энкодер и логистическая регрессия над его векторами."""

    encoder: SentenceEncoder
    threshold: float
    intercept: float
    weights: Vectors

    def probabilities(self, segments: tuple[str, ...]) -> Vectors:
        """Вероятность кризиса для каждого фрагмента."""
        scores: Vectors = self.encoder.encode(segments) @ self.weights
        probabilities: Vectors = 1 / (1 + np.exp(-(scores + self.intercept)))
        return probabilities


class EncoderCrisisDetector(ICrisisDetector):
    """Находит кризис по смыслу реплики: энкодер предложений и логистическая регрессия.

    Дополняет словарь неявными формулировками. Реплика оценивается целиком и по
    предложениям, чтобы длинный рассказ не размывал одну тревожную фразу.
    Классификатор отвечает только «кризис — нет», поэтому находка относится к
    косвенным признакам, а цитатой служит фрагмент с наибольшей вероятностью.
    Классификатор необязателен: реплики языка без него остаются словарному детектору.
    """

    def __init__(self, classifiers: Mapping[LanguageCode, _Classifier]) -> None:
        self._classifiers: Mapping[LanguageCode, _Classifier] = MappingProxyType(
            dict(classifiers),
        )

    @classmethod
    def load(
        cls,
        root: Path,
        languages: Iterable[LanguageCode],
        models: Path,
    ) -> "EncoderCrisisDetector":
        classifiers: dict[LanguageCode, _Classifier] = {}
        encoders: dict[str, SentenceEncoder] = {}

        for language in languages:
            path: Path = root / language / _CLASSIFIER_FILE
            if not path.is_file():
                continue

            document: ClassifierFile = read_yaml(path, ClassifierFile)
            if document.encoder not in encoders:
                encoders[document.encoder] = SentenceEncoder.load(models / document.encoder)
            classifiers[language] = cls._classifier(document, encoders[document.encoder])

        return cls(classifiers)

    @staticmethod
    def _classifier(document: ClassifierFile, encoder: SentenceEncoder) -> _Classifier:
        """Классификатор по файлу; веса должны подходить к векторам энкодера.

        Raises:
            ValueError: Число весов не совпадает с длиной вектора энкодера.
        """
        if len(document.weights) != encoder.dimension:
            raise ValueError(
                f"Classifier has {len(document.weights)} weights, "
                f"encoder '{document.encoder}' produces vectors of {encoder.dimension}",
            )

        classifier: _Classifier = _Classifier(
            encoder=encoder,
            threshold=document.threshold,
            intercept=document.intercept,
            weights=np.array(document.weights, dtype=np.float32),
        )
        return classifier

    @staticmethod
    def _segments(text: str) -> tuple[str, ...]:
        """Вся реплика и, если предложений больше одного, каждое из них."""
        whole: str = text.strip()
        sentences: list[str] = [
            sentence
            for sentence in (part.strip() for part in _SENTENCE_END.split(text))
            if any(char.isalnum() for char in sentence)
        ]

        segments: list[str] = [whole] if whole else []
        if len(sentences) > 1:
            segments += sentences
        return tuple(segments)

    @override
    async def detect(self, text: str, language: LanguageCode) -> tuple[CrisisSignal, ...]:
        signals: list[CrisisSignal] = []
        classifier: _Classifier | None = self._classifiers.get(language)
        segments: tuple[str, ...] = self._segments(text)

        if classifier is not None and segments:
            probabilities: Vectors = await asyncio.to_thread(classifier.probabilities, segments)
            best: int = int(probabilities.argmax())
            if probabilities[best] >= classifier.threshold:
                signals.append(
                    CrisisSignal(category=CrisisCategory.INDIRECT, quote=segments[best]),
                )

        return tuple(signals)
