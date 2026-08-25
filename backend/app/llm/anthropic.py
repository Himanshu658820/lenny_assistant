import time

import httpx

from app.config import settings
from app.core.errors import LLMProviderError
from app.llm.base import BaseLLMProvider, ChatMessage, ChatResult


class AnthropicProvider(BaseLLMProvider):
    name = "anthropic"

    def chat(self, messages: list[ChatMessage]) -> ChatResult:
        # ⬇️ THESE LINES MUST BE FIRST ⬇️
        if not settings.anthropic_api_key:
            raise LLMProviderError(
                "ANTHROPIC_API_KEY is not configured. Set it in .env or switch LLM_PROVIDER to ollama."
            )
        # ⬆️ THESE LINES MUST BE FIRST ⬆️

        system = "\n\n".join(m.content for m in messages if m.role == "system")
        conversation = [
            {"role": m.role, "content": m.content}
            for m in messages
            if m.role != "system"
        ]

        start = time.perf_counter()
        try:
            with httpx.Client(timeout=120.0) as client:
                response = client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": settings.anthropic_api_key,
                        "anthropic-version": "2023-06-01",
                    },
                    json={
                        "model": settings.anthropic_model,
                        "max_tokens": 2048,
                        "system": system or None,
                        "messages": conversation,
                    },
                )
        except httpx.HTTPError as exc:
            raise LLMProviderError(
                f"Anthropic request failed: {exc.__class__.__name__}"
            ) from exc

        if response.status_code >= 400:
            raise LLMProviderError(
                f"Anthropic error {response.status_code}: {response.text[:200]}"
            )

        data = response.json()
        latency_ms = int((time.perf_counter() - start) * 1000)
        content = "".join(block.get("text", "") for block in data.get("content", []))

        return ChatResult(
            content=content,
            provider=self.name,
            model=settings.anthropic_model,
            latency_ms=latency_ms,
            usage=data.get("usage"),
        )
