# -*- encoding: utf-8 -*-
# @Author: Leo Peng
# @Contact: leo@promptcn.com
from typing import List, Optional

import ollama


class Ollama:
    def __init__(self, host: str = "http://localhost:11434", model: str = None):
        self.host = host
        self.model = model
        self.client = ollama.Client(host=self.host)

    def __call__(self, prompt: str, history: Optional[List] = None, **kwargs):
        if not history:
            history = []

        try:
            response = self.client.chat(
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                model=self.model,
            )
        except ollama.ResponseError as exc:
            msg = str(exc)
            if "failed to load model" in msg or "llama-server" in msg:
                raise RuntimeError(
                    "本地 Ollama 无法加载模型（常见于 Windows 中文用户名路径）。"
                    "请退出 Ollama 托盘后执行 .\\scripts\\restart_ollama.ps1；"
                    "若需自定义模型目录，复制 scripts/ollama.local.ps1.example。"
                    f"原始错误：{msg}"
                ) from exc
            raise

        result = response["message"]["content"]
        return result
