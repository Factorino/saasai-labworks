from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Final, Protocol

import numpy as np
import numpy.typing as npt
import onnxruntime
from tokenizers import Encoding, Tokenizer


_MODEL_FILE: Final[str] = "model.onnx"
"""Энкодер в формате ONNX внутри каталога модели."""

_TOKENIZER_FILE: Final[str] = "tokenizer.json"
"""Токенизатор внутри каталога модели."""

_MAX_TOKENS: Final[int] = 256
"""Сколько токенов текста учитывается; реплики разбиваются на предложения раньше."""

type Vectors = npt.NDArray[np.floating[Any]]
"""Матрица векторов: строка — один текст."""

type _Ids = npt.NDArray[np.int64]
"""Матрица номеров токенов: строка — один текст."""


class _NodeArg(Protocol):
    """Описание входа или выхода модели ONNX."""

    @property
    def shape(self) -> Sequence[int | str | None]: ...


class _InferenceSession(Protocol):
    """То, чем энкодер пользуется в `onnxruntime.InferenceSession`: у пакета нет типов."""

    def get_outputs(self) -> Sequence[_NodeArg]: ...

    def run(self, output_names: None, input_feed: Mapping[str, _Ids]) -> Sequence[Any]: ...


class SentenceEncoder:
    """Превращает тексты в векторы единичной длины: среднее по токенам энкодера.

    Модель — каталог с `model.onnx` (энкодер со входами `input_ids`,
    `attention_mask`, `token_type_ids` и выходом `last_hidden_state`) и
    `tokenizer.json`.
    """

    def __init__(self, *, tokenizer: Tokenizer, session: _InferenceSession) -> None:
        self._tokenizer: Tokenizer = tokenizer
        self._session: _InferenceSession = session

    @classmethod
    def load(cls, directory: Path) -> "SentenceEncoder":
        """Загружает токенизатор и модель из каталога.

        Raises:
            FileNotFoundError: Файла модели или токенизатора нет: библиотеки
                сообщают об этом без пути, поэтому файлы проверяются заранее.
        """
        missing: list[str] = [
            str(path)
            for path in (directory / _TOKENIZER_FILE, directory / _MODEL_FILE)
            if not path.is_file()
        ]
        if missing:
            raise FileNotFoundError(f"Encoder files not found: {missing}")

        tokenizer: Tokenizer = Tokenizer.from_file(str(directory / _TOKENIZER_FILE))
        tokenizer.enable_truncation(max_length=_MAX_TOKENS)
        tokenizer.enable_padding()
        session: _InferenceSession = onnxruntime.InferenceSession(
            str(directory / _MODEL_FILE),
            providers=["CPUExecutionProvider"],
        )
        return cls(tokenizer=tokenizer, session=session)

    @property
    def dimension(self) -> int:
        """Длина вектора: последнее измерение выхода модели.

        Raises:
            TypeError: Длина в модели не задана числом.
        """
        size: int | str | None = self._session.get_outputs()[0].shape[-1]
        if not isinstance(size, int):
            raise TypeError(f"Encoder output size is not fixed: {size}")
        return size

    def encode(self, texts: Sequence[str]) -> Vectors:
        """Векторы текстов по порядку, строка матрицы — один текст."""
        encodings: list[Encoding] = self._tokenizer.encode_batch(list(texts))
        mask: _Ids = np.array([encoding.attention_mask for encoding in encodings], dtype=np.int64)

        hidden: Vectors = self._session.run(
            None,
            {
                "input_ids": np.array([encoding.ids for encoding in encodings], dtype=np.int64),
                "attention_mask": mask,
                "token_type_ids": np.array(
                    [encoding.type_ids for encoding in encodings],
                    dtype=np.int64,
                ),
            },
        )[0]
        weights: Vectors = mask[..., np.newaxis].astype(np.float32)
        pooled: Vectors = (hidden * weights).sum(axis=1) / weights.sum(axis=1)
        norms: Vectors = np.linalg.norm(pooled, axis=1, keepdims=True)

        vectors: Vectors = pooled / np.maximum(norms, np.finfo(np.float32).eps)
        return vectors
