import time

import httpx

from app.config import settings
from app.core.errors import LLMProviderError
from app.llm.base import BaseLLMProvider, ChatMessage, ChatResult


class OpenAIProvider(BaseLLMProvider):
    name = "openai"

    def chat(self, messages: list[ChatMessage]) -> ChatResult:
        if not settings.openai_api_key:
            raise LLMProviderError(
                "OPENAI_API_KEY is not configured. Set it in .env or switch LLM_PROVIDER to ollama."
            )

        start = time.perf_counter()
        try:
            with httpx.Client(timeout=120.0) as client:
                response = client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {settings.openai_api_key}"},
                    json={
                        "model": settings.openai_model,
                        "temperature": 0.2,
                        "messages": [
                            {"role": m.role, "content": m.content} for m in messages
                        ],
                    },
                )
        except httpx.HTTPError as exc:
            raise LLMProviderError(
                f"OpenAI request failed: {exc.__class__.__name__}"
            ) from exc

        if response.status_code >= 400:
            raise LLMProviderError(
                f"OpenAI error {response.status_code}: {response.text[:200]}"
            )

        data = response.json()
        latency_ms = int((time.perf_counter() - start) * 1000)

        return ChatResult(
            content=data["choices"][0]["message"]["content"],
            provider=self.name,
            model=settings.openai_model,
            latency_ms=latency_ms,
            usage=data.get("usage"),
        )
