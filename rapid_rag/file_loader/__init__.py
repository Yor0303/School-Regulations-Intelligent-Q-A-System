# -*- encoding: utf-8 -*-
# @Author: SWHL
# @Contact: liekkaskono@163.com

__all__ = ["FileLoader"]


def __getattr__(name):
    if name == "FileLoader":
        from .main import FileLoader

        return FileLoader
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
