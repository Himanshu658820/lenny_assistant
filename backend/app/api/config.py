from fastapi import APIRouter

from app.config import settings

router = APIRouter(prefix="/config", tags=["config"])


@router.get("/llm")
def llm_config():
    return {
        "current_provider": settings.llm_provider,
        "allow_request_override": True,
        "providers": {
            "ollama": {
                "configured": True,
                "chat_model": settings.ollama_chat_model,
                "embed_model": settings.ollama_embed_model,
            },
            "anthropic": {
                "configured": bool(settings.anthropic_api_key),
                "chat_model": settings.anthropic_model,
            },
            "openai": {
                "configured": bool(settings.openai_api_key),
                "chat_model": settings.openai_model,
            },
        },
    }
