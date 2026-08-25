import time
import json

import httpx

from app.config import settings
from app.core.errors import LLMProviderError
from app.llm.base import BaseLLMProvider, ChatMessage, ChatResult


def embed_texts(texts: list[str], batch_size: int = 8) -> list[list[float]]:
    embeddings: list[list[float]] = []

    with httpx.Client(timeout=120.0) as client:
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            response = client.post(
                f"{settings.ollama_base_url}/api/embed",
                json={"model": settings.ollama_embed_model, "input": batch},
            )
            _raise_for_ollama(response)
            embeddings.extend(response.json()["embeddings"])

    return embeddings


class OllamaProvider(BaseLLMProvider):
    name = "ollama"

    def chat(self, messages: list[ChatMessage]) -> ChatResult:
        payload = {
            "model": settings.ollama_chat_model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": False,
            "options": {"temperature": 0.2},
        }

        start = time.perf_counter()
        try:
            with httpx.Client(timeout=180.0) as client:
                response = client.post(
                    f"{settings.ollama_base_url}/api/chat", json=payload
                )
                _raise_for_ollama(response)
                data = response.json()
        except httpx.TimeoutException as exc:
            raise LLMProviderError(
                "Ollama timed out while generating a response."
            ) from exc
        except httpx.ConnectError as exc:
            raise LLMProviderError(
                "Ollama is not reachable. Is the Ollama service running?"
            ) from exc

        latency_ms = int((time.perf_counter() - start) * 1000)

        return ChatResult(
            content=data["message"]["content"],
            provider=self.name,
            model=data.get("model", settings.ollama_chat_model),
            latency_ms=latency_ms,
            usage={
                "prompt_tokens": data.get("prompt_eval_count"),
                "completion_tokens": data.get("eval_count"),
            },
        )

    def chat_stream(self, messages: list[ChatMessage]):
        payload = {
            "model": settings.ollama_chat_model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": True,
            "options": {"temperature": 0.2},
        }

        try:
            with httpx.Client(timeout=httpx.Timeout(180.0, read=None)) as client:
                with client.stream(
                    "POST", f"{settings.ollama_base_url}/api/chat", json=payload
                ) as response:
                    if response.status_code >= 400:
                        response.read()
                        raise LLMProviderError(
                            f"Ollama error {response.status_code}: {response.text[:200]}"
                        )

                    for line in response.iter_lines():
                        if not line:
                            continue
                        data = json.loads(line)
                        token = data.get("message", {}).get("content", "")
                        if token:
                            yield token
        except httpx.ConnectError as exc:
            raise LLMProviderError(
                "Ollama is not reachable. Is the Ollama service running?"
            ) from exc


def _raise_for_ollama(response: httpx.Response) -> None:
    if response.status_code >= 400:
        raise LLMProviderError(
            f"Ollama error {response.status_code}: {response.text[:200]}"
        )
