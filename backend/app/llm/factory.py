from app.config import settings
from app.core.errors import LLMProviderError
from app.llm.anthropic import AnthropicProvider
from app.llm.base import BaseLLMProvider
from app.llm.ollama import OllamaProvider
from app.llm.openai import OpenAIProvider

_PROVIDERS = {
    "ollama": OllamaProvider,
    "anthropic": AnthropicProvider,
    "openai": OpenAIProvider,
}


def get_provider(name: str | None = None) -> BaseLLMProvider:
    provider_name = (name or settings.llm_provider).strip().lower()
    cls = _PROVIDERS.get(provider_name)

    if cls is None:
        raise LLMProviderError(
            f"Unknown LLM provider '{provider_name}'. Use one of: {', '.join(_PROVIDERS)}."
        )

    return cls()
