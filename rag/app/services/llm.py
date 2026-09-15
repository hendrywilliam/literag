from langchain_openai import ChatOpenAI

from app.core.config import get_settings

_llm: ChatOpenAI | None = None


def get_llm() -> ChatOpenAI:
    global _llm
    if _llm is None:
        settings = get_settings()
        if not settings.llm_api_key:
            raise RuntimeError(
                "LLM_API_KEY is not set. Add it to .env to enable the "
                "relation-building agent and chains (e.g. QuestionToCypher)."
            )
        _llm = ChatOpenAI(
            model=settings.llm_model,
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
            temperature=0,
        )
    return _llm
