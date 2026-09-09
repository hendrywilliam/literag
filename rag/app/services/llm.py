from langchain_openai import ChatOpenAI

from app.core.config import get_settings

_llm: ChatOpenAI | None = None


def get_llm() -> ChatOpenAI:
    global _llm
    if _llm is None:
        settings = get_settings()
        if not settings.deepseek_api_key:
            raise RuntimeError(
                "DEEPSEEK_API_KEY is not set. Add it to .env to enable the "
                "relation-building agent."
            )
        _llm = ChatOpenAI(
            model=settings.deepseek_model,
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
            temperature=0,
        )
    return _llm
