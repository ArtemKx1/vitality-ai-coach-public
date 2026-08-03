from __future__ import annotations

from typing import Any

import ollama


class OllamaLLM:
    def __init__(self, model: str = "gemma4:e4b", temperature: float = 0.3, host: str = "http://localhost:11434"):
        self.model = model
        self.temperature = temperature
        self.host = host
        self.client = ollama.Client(host=host)

    def _options(self) -> dict:
        return {
            "temperature": self.temperature,
            "num_ctx": 8192,
            "top_k": 40,
            "top_p": 0.9,
        }

    def invoke(self, prompt: str) -> Any:
        response = self.client.chat(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            options=self._options(),
            keep_alive="10m",
        )
        return _Response(response["message"]["content"])

    def stream(self, prompt: str):
        stream = self.client.chat(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            options=self._options(),
            stream=True,
            keep_alive="10m",
        )
        for chunk in stream:
            delta = chunk.get("message", {}).get("content", "")
            if delta:
                yield delta

    def __str__(self) -> str:
        return f"OllamaLLM(model={self.model})"


class _Response:
    def __init__(self, content: str):
        self.content = content

    def __str__(self) -> str:
        return self.content
