# -*- encoding: utf-8 -*-
# @Author: SWHL
# @Contact: liekkaskono@163.com
from typing import List, Optional, Union

from sentence_transformers import SentenceTransformer


def resolve_device(device: str = "auto") -> str:
    if device != "auto":
        return device
    try:
        import torch

        if torch.cuda.is_available():
            return "cuda"
    except ImportError:
        pass
    return "cpu"


class EncodeText:
    def __init__(
        self,
        model_path: Optional[str] = None,
        device: str = "auto",
        batch_size: int = 16,
    ) -> None:
        if model_path is None:
            raise EncodeTextError("model_path is None.")
        resolved_device = resolve_device(device)
        self.model = SentenceTransformer(model_path, device=resolved_device)
        self.batch_size = batch_size
        self.device = resolved_device

    def __call__(self, sentences: Union[List[str], str]):
        if not isinstance(sentences, list):
            sentences = [sentences]
        show_progress = len(sentences) > 32
        return self.model.encode(
            sentences,
            batch_size=self.batch_size,
            show_progress_bar=show_progress,
        )


class EncodeTextError(Exception):
    pass
