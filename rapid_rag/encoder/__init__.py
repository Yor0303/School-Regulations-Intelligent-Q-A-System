# -*- encoding: utf-8 -*-
# @Author: SWHL
# @Contact: liekkaskono@163.com
from .sentence_transformer import EncodeText

__all__ = ["EncodeText", "ErnieEncodeText"]


def __getattr__(name):
    if name == "ErnieEncodeText":
        from .erniebot import ErnieEncodeText

        return ErnieEncodeText
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
