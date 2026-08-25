import logging

from app.agents.skills import artifact, grounded_chat, ship30, smalltalk
from app.llm.base import ChatMessage

logger = logging.getLogger("lenny.orchestrator")

SKILLS = {
    "smalltalk": smalltalk.run,
    "grounded_chat": grounded_chat.run,
    "ship30": ship30.run,
    "artifact": artifact.run,
}


def route(message: str) -> str:
    if smalltalk.is_smalltalk(message):
        return "smalltalk"

    lowered = message.lower()

    if "ship 30" in lowered or "ship30" in lowered or "essay" in lowered:
        return "ship30"

    if any(
        k in lowered
        for k in (
            "artifact",
            "html",
            "one-pager",
            "one pager",
            "dashboard",
            "markdown document",
            "cheat sheet",
        )
    ):
        return "artifact"

    return "grounded_chat"


def run(message: str, history: list[ChatMessage], provider) -> dict:
    skill_name = route(message)
    logger.info("routing to skill=%s provider=%s", skill_name, provider.name)
    return SKILLS[skill_name](message, history, provider)
