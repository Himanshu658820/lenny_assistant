import httpx
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from app.config import settings

router = APIRouter(prefix="/health", tags=["health"])


def check_database() -> tuple[bool, str]:
    try:
        engine = create_engine(settings.database_url, pool_pre_ping=True)

        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))

        engine.dispose()
        return True, "ok"

    except SQLAlchemyError as exc:
        return False, exc.__class__.__name__

    except Exception as exc:
        return False, exc.__class__.__name__


def check_ollama() -> tuple[bool, str]:
    try:
        response = httpx.get(
            f"{settings.ollama_base_url}/api/tags",
            timeout=3.0,
        )

        if response.status_code == 200:
            return True, "ok"

        return False, f"HTTP {response.status_code}"

    except Exception as exc:
        return False, exc.__class__.__name__


@router.get("/live")
def live():
    return {"status": "live"}


@router.get("/ready")
def ready():
    checks = {}
    ok = True

    db_ok, db_detail = check_database()
    checks["database"] = db_detail
    ok = ok and db_ok

    if settings.llm_provider == "ollama":
        ollama_ok, ollama_detail = check_ollama()
        checks["ollama"] = ollama_detail
        ok = ok and ollama_ok

    elif settings.llm_provider == "anthropic":
        checks["llm_provider"] = "anthropic"

        if not settings.anthropic_api_key:
            checks["anthropic"] = "missing_api_key"
            ok = False

    elif settings.llm_provider == "openai":
        checks["llm_provider"] = "openai"

        if not settings.openai_api_key:
            checks["openai"] = "missing_api_key"
            ok = False

    else:
        checks["llm_provider"] = settings.llm_provider

    body = {
        "status": "ready" if ok else "degraded",
        "llm_provider": settings.llm_provider,
        "checks": checks,
    }

    status_code = 200 if ok else 503

    return JSONResponse(content=body, status_code=status_code)
