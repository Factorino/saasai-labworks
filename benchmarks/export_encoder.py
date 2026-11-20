"""Экспортирует энкодер rubert-tiny2 в ONNX для кризисного классификатора.

Нужен один раз; PyTorch ставится во временное окружение и в зависимости сервиса
не входит. Запуск из корня репозитория:

    uv run --no-project --python 3.12 --index https://download.pytorch.org/whl/cpu \
        --with torch --with transformers --with onnx --with onnxruntime \
        python benchmarks/export_encoder.py
"""

import json
from pathlib import Path
from typing import Final

from huggingface_hub import HfApi, hf_hub_download
import numpy as np
from numpy.typing import NDArray
import onnxruntime
import torch
from transformers import AutoModel, AutoTokenizer, BatchEncoding, PreTrainedTokenizerBase


REPOSITORY: Final[str] = "cointegrated/rubert-tiny2"
TARGET: Final[Path] = Path("models/rubert-tiny2")


class _Encoder(torch.nn.Module):
    """Модель с тремя входами по порядку и одним выходом: так её можно трассировать."""

    def __init__(self, bert: torch.nn.Module) -> None:
        super().__init__()
        self.bert: torch.nn.Module = bert

    def forward(
        self,
        input_ids: torch.Tensor,
        attention_mask: torch.Tensor,
        token_type_ids: torch.Tensor,
    ) -> torch.Tensor:
        """Вернуть скрытые состояния последнего слоя."""
        hidden_state: torch.Tensor = self.bert(
            input_ids=input_ids,
            attention_mask=attention_mask,
            token_type_ids=token_type_ids,
        ).last_hidden_state
        return hidden_state


def main() -> None:
    TARGET.mkdir(parents=True, exist_ok=True)
    revision: str | None = HfApi().model_info(REPOSITORY).sha
    hf_hub_download(REPOSITORY, "tokenizer.json", revision=revision, local_dir=TARGET)
    bert: torch.nn.Module = AutoModel.from_pretrained(REPOSITORY, revision=revision).eval()
    model: _Encoder = _Encoder(bert).eval()
    tokenizer: PreTrainedTokenizerBase = AutoTokenizer.from_pretrained(
        REPOSITORY,
        revision=revision,
    )
    sample: BatchEncoding = tokenizer(["Проверка экспорта энкодера"], return_tensors="pt")
    arguments: tuple[torch.Tensor, torch.Tensor, torch.Tensor] = (
        sample["input_ids"],
        sample["attention_mask"],
        sample["token_type_ids"],
    )
    names: list[str] = ["input_ids", "attention_mask", "token_type_ids"]
    path: Path = TARGET / "model.onnx"
    torch.onnx.export(
        model,
        arguments,
        str(path),
        input_names=names,
        output_names=["last_hidden_state"],
        dynamic_axes={
            **{name: {0: "batch", 1: "tokens"} for name in names},
            "last_hidden_state": {0: "batch", 1: "tokens"},
        },
        opset_version=17,
        dynamo=False,
    )
    session: onnxruntime.InferenceSession = onnxruntime.InferenceSession(
        str(path),
        providers=["CPUExecutionProvider"],
    )
    exported: NDArray[np.float32] = session.run(
        None,
        {name: sample[name].numpy() for name in names},
    )[0]
    model.eval()  # Экспорт возвращает модель в режим обучения.
    with torch.no_grad():
        original: NDArray[np.float32] = model(*arguments).numpy()
    if not np.allclose(exported, original, atol=1e-4):
        raise ValueError("The exported model differs from the original one")
    (TARGET / "source.json").write_text(
        json.dumps({"repository": REPOSITORY, "revision": revision}, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"{path}: {path.stat().st_size / 2**20:.0f} MB, revision {revision}")


if __name__ == "__main__":
    main()
