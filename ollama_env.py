# -*- encoding: utf-8 -*-
"""Apply Ollama model directory from project config (OLLAMA_MODELS)."""
import os
from pathlib import Path
from typing import Any

from rapid_rag.utils import read_yaml

CONFIG_PATH = Path("rapid_rag/config.yaml")
LOCAL_CONFIG_PATH = Path("rapid_rag/config.local.yaml")
OLLAMA_CLIENT_KEYS = frozenset({"host", "model"})


def _deep_merge(base: dict, override: dict) -> dict:
    merged = dict(base)
    for key, value in override.items():
        if (
            key in merged
            and isinstance(merged[key], dict)
            and isinstance(value, dict)
        ):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_merged_config() -> dict[str, Any]:
    config = read_yaml(CONFIG_PATH)
    if LOCAL_CONFIG_PATH.is_file():
        local = read_yaml(LOCAL_CONFIG_PATH)
        config = _deep_merge(config, local)
    return config


def filter_ollama_client_kwargs(params: dict) -> dict:
    """Strip config-only keys (e.g. models_path) before Ollama client init."""
    return {key: value for key, value in params.items() if key in OLLAMA_CLIENT_KEYS}


def get_configured_models_path() -> Path | None:
    config = load_merged_config()
    ollama_cfg = config.get("LLM_API", {}).get("Ollama", {})
    raw = ollama_cfg.get("models_path")
    if not raw:
        return None
    return Path(raw).expanduser()


def apply_ollama_env(force_from_config: bool = True) -> str:
    """
    Set OLLAMA_MODELS for this process when config.local.yaml defines a valid path.

    Teammates without local config keep system / Ollama default model directory.
  """
    configured = get_configured_models_path()
    if configured is None:
        return os.environ.get("OLLAMA_MODELS", "")

    resolved = configured.resolve()
    if not resolved.is_dir():
        return os.environ.get("OLLAMA_MODELS", "")

    if force_from_config or not os.environ.get("OLLAMA_MODELS"):
        os.environ["OLLAMA_MODELS"] = str(resolved)
    return os.environ.get("OLLAMA_MODELS", "")


def validate_models_directory(path: Path | None = None) -> tuple[bool, str]:
    path = path or get_configured_models_path()
    if path is None:
        return True, "未配置本地 models_path（使用 Ollama 默认模型目录）"
    if not path.is_dir():
        return False, f"本地 models_path 不存在：{path}"
    blobs = path / "blobs"
    manifests = path / "manifests"
    if not blobs.is_dir():
        return False, f"缺少 blobs 目录：{blobs}"
    if not manifests.is_dir():
        return False, f"缺少 manifests 目录：{manifests}"
    return True, str(path.resolve())
