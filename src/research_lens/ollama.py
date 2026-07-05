"""Ollama model adapter for SQL generation."""

from __future__ import annotations

import httpx


class OllamaResponseError(ValueError):
    """Raised when Ollama returns a response without usable model content."""


def generate_ollama_sql(
    prompt: str,
    *,
    base_url: str,
    model: str,
    timeout_seconds: float = 300.0,
    client: httpx.Client | None = None,
) -> str:
    requester = client or httpx
    response = requester.post(
        f"{base_url.rstrip('/')}/api/chat",
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "think": False,
            "keep_alive": "10m",
            "options": {
                "temperature": 0,
                "num_predict": 384,
            },
        },
        timeout=timeout_seconds,
    )
    response.raise_for_status()

    try:
        content = response.json()["message"]["content"]
    except (KeyError, TypeError, ValueError) as error:
        raise OllamaResponseError("Ollama response is missing message content") from error

    if not isinstance(content, str) or not content.strip():
        raise OllamaResponseError("Ollama returned empty message content")

    return content
